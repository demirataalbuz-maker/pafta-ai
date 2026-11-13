---
id: ai-olay-07
title: "Rules File Backdoor · Gizli Unicode ve İnceleme Sonrası Hash"
summary: Kod ajanlarının kural dosyalarındaki (.cursorrules / copilot-instructions) görünmez Unicode karakterlerini ve inceleme sonrası hash kaymasını yakala, ölç ve satır bazlı raporla.
esleme: ai-saldiri-52, ai-saldiri-47, ai-savunma-20, ai-savunma-21
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Mart 2025'te *Pillar Security* araştırmacıları, **Rules File Backdoor** adıyla yayımladıkları teknik raporda yapay zekâ kod asistanlarının proje yapılandırma ve kural dosyalarına (`.cursor/rules`, `.github/copilot-instructions.md` vb.) yerleştirilen **görünmez Unicode karakterlerinin** (`zero-width joiners`, `bidirectional overrides`, `Unicode Tags`) kod inceleme ekranlarında fark edilmeden geçebildiğini ve geliştirici depoyu klonladığında ajanın ürettiği koda gizli arka kapı talimatları enjekte edebildiğini gösterdi.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu derste gerçek bir IDE eklentisi veya canlı kod modeli çalıştırılmaz. Depoya giren kural dosyalarının **kod noktası hijyeni**, **kriptografik SHA-256 bütünlüğü** ve **insan inceleme bayrağı (`incelendi`)** ile nasıl kapıdan geçirileceği çevrimdışı Python modeliyle sınanır.
:::

::: anlat 2. Mekanizma · kural dosyaları neden tedarik zinciri yüzeyidir?
Paylaşılan bir kod deposundaki kural dosyası her istemin başına otomatik eklenen kalıcı bir **sistem yönergesi uzantısıdır** (`ai-saldiri-47`, `ai-savunma-20`). Bu yüzeyde iki ayrı saldırı vektörü birleşir:

1. **Görsel gizleme (`Trojan Source` + `ASCII Smuggling`):** `U+200B` (*ZWSP*), `U+200C`/`U+200D` (*ZWNJ/ZWJ*), `U+202A..U+202E` ve `U+2066..U+2069` (*bidi yön değiştiriciler*) ile `U+E0000..U+E007F` (*Tags*) karakterleri PR inceleme ekranında gizli yönerge taşır.
2. **İnceleme sonrası kayma (`rug pull` / `TOCTOU`):** Geliştirici temiz sürümü inceleyip onayladıktan sonra (`incelendi = True`) dosya içeriği değişirse eski onay geçersiz sayılmalıdır; onay doğrudan içeriğin **UTF-8 SHA-256** özetine bağlanır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız `\u200b` (*ZWSP*) karakterini aramak | `\u200d` (*ZWJ*), `\u202e` (*RLO*) ve `U+E0000..U+E007F` karakterlerini kaçırır | Sıfır genişlik + `bidi` aralıkları + `Tags` bloğunun tamamını reddetmek |
| `if incelendi:` ile gevşek kontrol yapmak | `incelendi=1` veya `'evet'` gibi bozuk bayrakları kabul eder | `incelendi is True` tam kimlik kontrolü |
| Onayı dosya adına bağlamak | İncelemeden sonra yapılan tek baytlık değişiklik fark edilmez | `hmac.compare_digest(sha256(icerik), onay_sha256)` ile içeriğe bağlamak |
:::

::: tahmin İncelenen metin ile çalıştırılan metin neden aynı SHA-256 özetini taşımalıdır?
Ekranda aynı görünen iki kural dizgesinin SHA-256 özeti karşılaştırıldığında ne çıkar?

```python
import hashlib

temiz = 'Yalnız standart kütüphane kullan.'
gizli = 'Yalnız standart\u200d kütüphane kullan.'
h_temiz = hashlib.sha256(temiz.encode('utf-8')).hexdigest()
h_gizli = hashlib.sha256(gizli.encode('utf-8')).hexdigest()
print('uzunluklar:', len(temiz), len(gizli))
print('özetler aynı mı:', h_temiz == h_gizli)
```

???

```cikti
uzunluklar: 33 34
özetler aynı mı: False
```
Görsel fark sıfır olsa bile tek bir `\u200d` (*Zero Width Joiner*) bayt dizisini ve SHA-256 özetini tamamen değiştirir. Kod noktası taraması ilk yüklemede gizli karakteri yakalar; SHA-256 kilidi ise onay sonrası sessiz değişimi yakalar.
:::

::: gorev 1 · Kural dosyası bütünlük ve görünmez Unicode kapısını (`kural_kabul`) kur
`kural_kabul(icerik, onay_sha256, incelendi)` işlevini yaz:

- `icerik` ve `onay_sha256` `str` türünde olmalı ve `incelendi is True` olmalı; aksi halde `False` döndür.
- `icerik` içinde aşağıdaki gizli/yönlendirici kod noktalarından **herhangi biri** geçiyorsa SHA-256 eşleşse bile her durumda `False` döndür:
  - Sıfır genişlikli küme: `U+200B`, `U+200C`, `U+200D`, `U+2060`, `U+FEFF`;
  - Çift yönlü (`bidi`) kontrol aralıkları: `0x202A <= ord(c) <= 0x202E` ve `0x2066 <= ord(c) <= 0x2069`;
  - Unicode `Tags` bloğu: `0xE0000 <= ord(c) <= 0xE007F`.
- `onay_sha256` tam 64 küçük onaltılık karakter olmalı ve `icerik.encode('utf-8')` üzerinden hesaplanan SHA-256 özetiyle `hmac.compare_digest` ile birebir eşleşmelidir.

KUSURLU başlangıç yalnız `\u200b` karakterine bakıyor ve `incelendi` için gevşek doğruluk (`bool`) kullanıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "test",\n  "0000000000000000000000000000000000000000000000000000000000000000",\n  true\n]', encoding='utf-8')
```

```starter
import hashlib

def kural_kabul(icerik, onay_sha256, incelendi):
    if not isinstance(icerik, str) or '\u200b' in icerik:
        return False
    return bool(incelendi) and hashlib.sha256(icerik.encode('utf-8')).hexdigest() == onay_sha256

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(kural_kabul(*_args))
```

```solution
import hashlib
import hmac

_GIZLI_TEKIL = {'\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'}

def _yasak_kod_var(metin):
    for c in metin:
        kod = ord(c)
        if (c in _GIZLI_TEKIL
                or (0x202A <= kod <= 0x202E)
                or (0x2066 <= kod <= 0x2069)
                or (0xE0000 <= kod <= 0xE007F)):
            return True
    return False

def kural_kabul(icerik, onay_sha256, incelendi):
    if not isinstance(icerik, str) or not isinstance(onay_sha256, str) or incelendi is not True:
        return False
    if len(onay_sha256) != 64 or any(c not in '0123456789abcdef' for c in onay_sha256):
        return False
    if _yasak_kod_var(icerik):
        return False
    ozet = hashlib.sha256(icerik.encode('utf-8')).hexdigest()
    return hmac.compare_digest(ozet, onay_sha256)

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(kural_kabul(*_args))
```

```test
need('kural_kabul')
import hashlib

_temiz = 'Proje kuralı: tüm SQL sorguları parametreli yazılır.'
_ozet = hashlib.sha256(_temiz.encode('utf-8')).hexdigest()
eq(kural_kabul(_temiz, _ozet, True), True, 'incelenmiş, temiz ve özeti eşleşen kural kabul edilmeli')

eq(kural_kabul(_temiz, _ozet, False), False, 'incelenmemiş kural reddedilmeli')
eq(kural_kabul(_temiz, _ozet, 1), False, 'int 1 incelendi bayrağı sayılmaz')
eq(kural_kabul(_temiz + ' ', _ozet, True), False, 'inceleme sonrası tek boşluk değişimi bile yakalanmalı')
eq(kural_kabul(_temiz, _ozet.upper(), True), False, 'büyük harfli SHA-256 reddedilmeli')

for _gizli_kar in ('\u200b', '\u200c', '\u200d', '\u2060', '\ufeff', '\u202a', '\u202e', '\u2066', '\u2069', chr(0xE0000), chr(0xE0041), chr(0xE007F)):
    _zehirli = 'Kural ' + _gizli_kar + ' metni'
    _z_ozet = hashlib.sha256(_zehirli.encode('utf-8')).hexdigest()
    eq(kural_kabul(_zehirli, _z_ozet, True), False, f'özeti eşleşse bile U+{ord(_gizli_kar):04X} içeren kural reddedilmeli')

for _bozuk in ((None, _ozet, True), (_temiz, None, True), (123, _ozet, True)):
    eq(kural_kabul(*_bozuk), False, 'bozuk türler False dönmeli')

# Biçim kontrolü gereklidir: hmac.compare_digest ASCII olmayan str ile TypeError fırlatır.
eq(kural_kabul(_temiz, 'ğ' * 64, True), False, 'ASCII olmayan 64 karakterlik onay False dönmeli, hata fırlatmamalı')
eq(kural_kabul(_temiz, 'ğ' * 63, True), False, 'yanlış uzunlukta ASCII olmayan onay False dönmeli')

# Yasaklı aralıkların komşuları sözleşme dışıdır (Sınır bölümüne bakın): özeti eşleşen kural kabul edilir.
for _komsu in (' ', ' ', '⁥', '⁪', chr(0xDFFFF), chr(0xE0080)):
    _metin = 'Kural ' + _komsu + ' metni'
    eq(kural_kabul(_metin, hashlib.sha256(_metin.encode('utf-8')).hexdigest(), True), True,
       f'yasaklı aralığın komşusu U+{ord(_komsu):04X} bu kurala girmez')
```

```hint
`incelendi is True` şartından sonra tüm gizli/bidi/Tag kod noktalarını tara; en sonda `hashlib.sha256(icerik.encode('utf-8')).hexdigest()` ile `onay_sha256` değerini `hmac.compare_digest` ile karşılaştır.
```
:::

::: gorev 2 · Açık ve yamalı kural kapısını senaryo vakalarında ölç
`kural_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (icerik, onay_sha256, incelendi), ...}` sözlüğüdür. Geçersiz liste, şema veya çağrılamayan sınırda `ValueError` fırlat.
- Sınır işlevi `True` döndürdüğünde kural dosyası **yüklendi** sayılır.
- Saldırı vakalarında yükleme **arka kapı sızıntısı (`sizma`)**, meşru vakalarda yükleme **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `sonra_sizma` yerine yanlışlıkla iki kez `acik_fn` çağırıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def kural_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    oran = round(sum(1 for v in s if acik_fn(*v['girdi'])) / len(s), 4) if s else None
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': oran, 'sonra_sizma': oran,
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi'])) / len(m), 4) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def kural_senaryo_olc(vakalar, acik_fn, yamali_fn):
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
need('kural_senaryo_olc')
import hashlib, hmac
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(icerik, onay_sha256, incelendi):
    if not isinstance(icerik, str) or not isinstance(onay_sha256, str) or incelendi is not True:
        return False
    if any(c in {'\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'} or (0x202A <= ord(c) <= 0x202E) or (0x2066 <= ord(c) <= 0x2069) or (0xE0000 <= ord(c) <= 0xE007F) for c in icerik):
        return False
    return hmac.compare_digest(hashlib.sha256(icerik.encode('utf-8')).hexdigest(), onay_sha256)

_vakalar = senaryo_vakalari(7, tohum=2)
eq(kural_senaryo_olc(_vakalar, acik_sinir(7), _yama), {
    'saldiri_n': 5,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 5/5 saldırıyı geçirir, yama 0.0 sızıntı ve 1.0 kabul sağlar')

eq(kural_senaryo_olc(_vakalar, acik_sinir(7), lambda *_a: False)['regresyon_n'], 2, 'her kuralı reddeden yama 2 regresyon üretir')
raises(ValueError, kural_senaryo_olc, [], acik_sinir(7), _yama, msg='boş liste ValueError')

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
eq(kural_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(kural_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(kural_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(kural_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
eq(kural_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
raises(ValueError, kural_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, kural_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, kural_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, kural_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Her vakada `acik_fn` ve `yamali_fn` işlevlerini ayrı `deepcopy` argümanlarıyla çalıştırıp `s_once` ve `s_sonra` toplamlarını ayrı tut.
```
:::

::: gorev 3 · CI/PR hattı için satır bazlı gizli Unicode denetim raporu üret
CI boru hattında geliştiriciye tam olarak hangi satırda hangi gizli karakterin bulunduğunu raporlayan `kural_fark_raporu(icerik)` işlevini yaz:

- `icerik` `str` değilse `ValueError` fırlat.
- Metni `icerik.splitlines()` ile `1` tabanlı satır numaralarıyla (`1, 2, ...`) tara.
- Görev 1'deki yasaklı karakter kümelerinden (`U+200B..U+200D`, `U+2060`, `U+FEFF`, `0x202A..0x202E`, `0x2066..0x2069`, `0xE0000..0xE007F`) bulunan her karakter için sırayla `{'satir': satir_no, 'kod': f'U+{ord(c):04X}'}` kaydı ekle (4 haneden uzun kodlarda `04X` otomatik 5 hane üretir, örn. `'U+E0041'`).
- Dönüş: `{'temiz': bool, 'ham_uzunluk': int, 'bulgular': list[dict]}` (`ham_uzunluk = len(icerik)`).

KUSURLU başlangıç satır numarasını `0` tabanlı veriyor ve `bidi` karakterlerini atlıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def kural_fark_raporu(icerik):
    bulgular = []
    for i, satir in enumerate(icerik.splitlines()):
        for c in satir:
            if 0xE0000 <= ord(c) <= 0xE007F:
                bulgular.append({'satir': i, 'kod': f'U+{ord(c):04X}'})
    return {'temiz': not bulgular, 'ham_uzunluk': len(icerik), 'bulgular': bulgular}
```

```solution
_YASAK_TEKIL = {'\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'}

def kural_fark_raporu(icerik):
    if not isinstance(icerik, str):
        raise ValueError('icerik str olmali')
    bulgular = []
    for satir_no, satir in enumerate(icerik.splitlines(), start=1):
        for c in satir:
            kod = ord(c)
            if (c in _YASAK_TEKIL
                    or (0x202A <= kod <= 0x202E)
                    or (0x2066 <= kod <= 0x2069)
                    or (0xE0000 <= kod <= 0xE007F)):
                bulgular.append({'satir': satir_no, 'kod': f'U+{kod:04X}'})
    return {
        'temiz': len(bulgular) == 0,
        'ham_uzunluk': len(icerik),
        'bulgular': bulgular,
    }
```

```test
need('kural_fark_raporu')
_dosya = 'Satır 1 temiz\nSatır 2\u202e yön\nSatır 3' + chr(0xE0041) + '\u200b'
eq(kural_fark_raporu(_dosya), {
    'temiz': False,
    'ham_uzunluk': len(_dosya),
    'bulgular': [
        {'satir': 2, 'kod': 'U+202E'},
        {'satir': 3, 'kod': 'U+E0041'},
        {'satir': 3, 'kod': 'U+200B'},
    ],
}, '1-tabanlı satır numaraları ve tam U+XXXX kodları dönmeli')
eq(kural_fark_raporu('Temiz satır 1\nTemiz satır 2'), {
    'temiz': True,
    'ham_uzunluk': 27,
    'bulgular': [],
}, 'temiz dosya onaylanmalı')
raises(ValueError, kural_fark_raporu, 123, msg='str dışı girdi reddedilmeli')

# Her aralığın iki ucu ve iki komşusu (U+2029 satır ayırıcıdır, splitlines onu zaten böler).
_uclar = ['‪', '‮', '⁦', '⁩', chr(0xE0000), chr(0xE007F)]
eq(kural_fark_raporu(''.join(_uclar))['bulgular'], [{'satir': 1, 'kod': f'U+{ord(c):04X}'} for c in _uclar],
   'her yasaklı aralığın iki ucu da raporlanmalı')
_komsular = ' ⁥⁪' + chr(0xDFFFF) + chr(0xE0080)
eq(kural_fark_raporu(_komsular), {'temiz': True, 'ham_uzunluk': 5, 'bulgular': []},
   'aralık dışındaki komşu kod noktaları raporlanmaz')
```

```hint
`enumerate(icerik.splitlines(), start=1)` ile 1 tabanlı satır numarasını kur; `f'U+{kod:04X}'` biçimi hem `'U+202E'` hem `'U+E0041'` dizgelerini doğru üretir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "Pillar Security'nin *Rules File Backdoor* araştırması, depolardaki `.cursorrules` ve `copilot-instructions` dosyalarının görünmez Unicode karakterleriyle kod ajanına arka kapı talimatı taşıyabildiğini gösterdi."
2. **Çift tehdit (30 sn).** "İlk tehdit PR ekranında görünmeyen `bidi` / `Tag` kod noktaları, ikincisi ise inceleme sonrasında dosyanın sessizce değiştirilmesidir."
3. **Sınır ve ölçüm (30 sn).** "`kural_kabul` içinde kod noktası taraması, `incelendi is True` ve `compare_digest` SHA-256 doğrulamasını birleştirdim; senaryo koşusunda 5/5 saldırı durduruldu."
4. **CI görünürlüğü (25 sn).** "`kural_fark_raporu` ile PR kontrolünde gizli karakterleri satır numarası ve `U+XXXX` koduyla görünür kıldım."
5. **Kapanış (20 sn).** "Ajan kural dosyaları düz dokümantasyon değil, yürütülebilir yapılandırma kodu (`code-as-policy`) olarak korunmalıdır."
:::

::: anlat Sınır ve kaynak
Bu dersteki kontroller görünmez/yönlendirici Unicode gizlemesini ve onay sonrası hash kaymasını yakalar. Saldırgan kural dosyasına tamamen görünür, düz ASCII doğal dille yanıltıcı ama meşru görünümlü bir mimari kural ("güvenlik hız için atlanabilir" gibi) yazarsa bunu karakter tarayıcısı değil, `CODEOWNERS` zorunlu insan incelemesi yakalar (`ai-savunma-21`).

Karakter kümesi de bilinçli olarak dardır: Trojan Source'un kullandığı `bidi` denetimleri, sıfır genişlikli beş karakter ve `Tags` bloğu. Unicode'un görüntülenmeyen karakterlerinin tamamı (`Default_Ignorable_Code_Point` özelliği) bundan geniştir; örneğin kullanımdan kalkmış biçim karakterleri `U+206A..U+206F` ve `U+180E` bu kurala girmez ve testler de bunu sözleşme olarak sınar. Üretimde liste elle yazılmaz; Unicode karakter veritabanındaki özellikten (`DerivedCoreProperties.txt`) üretilir.

- Birincil kaynak: [Pillar Security — New Vulnerability in GitHub Copilot and Cursor: How Hackers Can Weaponize Code Agents (Mart 2025)](https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Depodaki `.github/CODEOWNERS` dosyasına `.cursor/rules/**` ve `.github/copilot-instructions.md` yollarını eklemek, Görev 1'deki `incelendi` bayrağının hangi kurumsal karşılığını sağlar?
:::

::: ozet
- Kod ajanı kural dosyaları her isteme eklendiği için yüksek etkili tedarik zinciri yüzeyidir.
- Hem sıfır genişlik / `bidi` / `Tags` karakterleri taranmalı hem de onay SHA-256 özetine bağlanmalıdır.
- CI hattında satır bazlı `U+XXXX` raporu görsel inceleme körlüğünü ortadan kaldırır.
:::
