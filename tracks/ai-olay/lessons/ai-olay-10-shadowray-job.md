---
id: ai-olay-10
title: "Ray İş Gönderimi · Ağ Varsayımı, Kimlik Doğrulama ve En Az Ayrıcalık"
summary: Tartışmalı CVE-2023-48022 (ShadowRay) bağlamında iç ağ varsayımının neden kimlik doğrulama yerine geçmediğini incele; iş gönderme kapısını, senaryo ölçümünü ve argüman şemasını kur.
esleme: ai-saldiri-19, ai-saldiri-20, ai-savunma-11, ai-savunma-13
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Mart 2024'te *Oligo Security*, internete açık bırakılmış **Ray** kümelerinin kimlik doğrulamasız iş gönderme (`Jobs API`) ucu üzerinden gerçek saldırılarda istismar edildiğini (*ShadowRay*) raporladı. İlgili **CVE-2023-48022** kaydı üretici (Anyscale) tarafından **tartışmalı (`DISPUTED`)** olarak işaretlenmiştir: üretici dokümantasyonu Ray panelinin zaten güvenilir/kontrollü bir ağ sınırı içinde çalıştırılmak üzere tasarlandığını ve yerleşik kimlik doğrulama iddiası taşımadığını belirtir; araştırmacılar ise varsayılan kimliksiz yönetim uçlarının bulut ve iç ağ yayılımında kritik risk doğurduğunu vurgular.

> [!NOTE]
> **Kaynak dürüstlüğü ve yerel kopya:** Bu derste üreticinin kontrollü ağ varsayımı ile sahadaki yanlış yapılandırma riski arasındaki mimari gerilim olduğu gibi korunur; hiçbir Ray kümesi başlatılmaz ve hiçbir işletim sistemi süreci (`subprocess`) çalıştırılmaz.
:::

::: anlat 2. Mekanizma · "iç ağdayız" varsayımı neden Sıfır Güven (`Zero Trust`) ilkesinde yetmez?
Dağıtık eğitim ve çıkarım kümelerinde iş gönderme (`job submit`) ucu doğası gereği küme düğümlerinde kod çalıştırır; yani GPU belleklerine, model ağırlıklarına ve ortam değişkenlerindeki bulut kimlik bilgilerine erişir (`ai-saldiri-19`, `ai-savunma-13`). Yalnız ağ bölgesine (`bolge == 'yonetim'`) güvenmek üç yoldan kırılır:

1. **SSRF ve vekil atlatma:** Aynı iç ağdaki bir web/ajan servisi `AI-SSRF` zafiyeti taşıdığında iç yönetim portuna istek gönderebilir.
2. **Yatay hareket (`lateral movement`):** Tek bir geliştirici iş istasyonu ele geçirildiğinde kimliksiz yönetim API'si tüm GPU kümesini teslim eder.
3. **Rol ayrımı eksikliği:** Küme metriklerini izleme yetkisi (`'viewer'` / `'metrics-read'`) olan bir kimliğin iş gönderme (`'job-submit'`) yetkisi olmamalıdır (`RBAC`).

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `bolge == 'yonetim'` ise kimlik sormadan izin vermek | İç ağdaki SSRF veya tek ele geçirilen makine tüm kümeyi ele geçirir | Ağ sınırı + `kimlik_dogrulandi is True` + `'job-submit'` rolü |
| `if kimlik_dogrulandi:` ile gevşek kontrol | `1` veya `'misafir'` gibi bozuk bayrakları doğrulanmış sayar | `kimlik_dogrulandi is True` |
| `roller` listesinin eleman türlerini denetlememek veya `'job-submit' in roller` dizge üzerinde çalıştırmak | `roller = 'job-submit-degil'` dizgesinde alt dizge eşleşmesi `True` döner! | `isinstance(roller, list)` ve `all(isinstance(r, str) for r in roller)` |
:::

::: tahmin `roller` bir `list` yerine `str` gelirse `'job-submit' in roller` ne döndürür?
Python'da `in` işleci hem listede eleman arar hem dizgede alt dizge arar; tür kontrolü unutulursa ne olur?

```python
sahte_roller = 'no-job-submit-allowed'
gevsek = 'job-submit' in sahte_roller
siki = isinstance(sahte_roller, list) and 'job-submit' in sahte_roller
print('gevşek kontrol:', gevsek)
print('sıkı liste kontrolü:', siki)
```

???

```cikti
gevşek kontrol: True
sıkı liste kontrolü: False
```
`'no-job-submit-allowed'` dizgesi tam tersini söylediği halde içinde `'job-submit'` alt dizgesi geçtiği için `isinstance(roller, list)` kontrolü olmayan bir kapıdan `True` olarak geçer!
:::

::: gorev 1 · Ağ, kimlik ve rol doğrulamalı `job_izin` kapısını kur
`job_izin(bolge, kimlik_dogrulandi, roller)` işlevini yaz (hiçbir iş veya alt süreç başlatma):

- Yalnız aşağıdaki koşulların **tamamı** sağlandığında `True`, diğer her durumda ve bozuk türlerde `False` döndür:
  1. `bolge == 'yonetim'`;
  2. `kimlik_dogrulandi is True`;
  3. `roller` bir `list` olmalı, içindeki **tüm** öğeler boş olmayan `str` olmalı ve `'job-submit'` listede eleman olarak bulunmalı.

KUSURLU başlangıç yalnız `bolge == 'yonetim'` kontrolüne güvendiği için iç yönetim ağından gelen kimliksiz ve yetkisiz işleri kabul ediyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "internet",\n  true,\n  [\n    "job-submit"\n  ]\n]', encoding='utf-8')
```

```starter
def job_izin(bolge, kimlik_dogrulandi, roller):
    return bolge == 'yonetim'

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(job_izin(*_args))
```

```solution
def job_izin(bolge, kimlik_dogrulandi, roller):
    return (
        bolge == 'yonetim'
        and kimlik_dogrulandi is True
        and isinstance(roller, list)
        and all(isinstance(r, str) and bool(r.strip()) for r in roller)
        and 'job-submit' in roller
    )

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(job_izin(*_args))
```

```test
need('job_izin')
eq(job_izin('yonetim', True, ['job-submit']), True, 'yönetim ağında doğrulanmış job-submit rolü geçmeli')
eq(job_izin('yonetim', True, ['viewer', 'job-submit']), True, 'çoklu meşru rolde job-submit geçmeli')

_red = [
    ('internet', True, ['job-submit']),
    ('kume-disi', True, ['job-submit']),
    ('yonetim', False, ['job-submit']),
    ('yonetim', 1, ['job-submit']),
    ('yonetim', 'true', ['job-submit']),
    ('yonetim', True, ['viewer']),
    ('yonetim', True, []),
    ('yonetim', True, 'no-job-submit-allowed'),
    ('yonetim', True, ('job-submit',)),
    ('yonetim', True, ['job-submit', 123]),
    ('yonetim', True, ['job-submit', '']),
    (None, True, ['job-submit']),
]
for _args in _red:
    eq(job_izin(*_args), False, f'yetkisiz veya bozuk iş isteği reddedilmeli: {_args!r}')
```

```hint
`bolge == 'yonetim'`, `kimlik_dogrulandi is True`, `isinstance(roller, list)`, `all(isinstance(r, str) and bool(r.strip()) for r in roller)` ve `'job-submit' in roller` koşullarını birleştir.
```
:::

::: gorev 2 · Açık ve yamalı küme kapısını senaryo vakalarında ölç
`ray_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (bolge, kimlik_dogrulandi, roller), ...}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Sınır işlevi `True` döndürdüğünde iş **kümeye kabul edildi** sayılır.
- Saldırı vakalarında kabul **yetkisiz iş yürütme (`sizma`)**, meşru vakalarda kabul **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `regresyon_n` alanını her zaman `0` bırakıyor ve boş gruplarda `ZeroDivisionError` üretiyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def ray_senaryo_olc(vakalar, acik_fn, yamali_fn):
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

def ray_senaryo_olc(vakalar, acik_fn, yamali_fn):
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
need('ray_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(b, k, r):
    return b == 'yonetim' and k is True and isinstance(r, list) and all(isinstance(x, str) and x.strip() for x in r) and 'job-submit' in r

_vakalar = senaryo_vakalari(10, tohum=10)
eq(ray_senaryo_olc(_vakalar, acik_sinir(10), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'yönetim ağına körü körüne güvenen açık sınır 4/4 sızdırır, RBAC yaması 0.0 yapar')

eq(ray_senaryo_olc(_vakalar, acik_sinir(10), lambda *_a: False)['regresyon_n'], 2, 'tüm işleri kapatan sınır 2 regresyon üretir')
eq(ray_senaryo_olc([v for v in _vakalar if v['saldiri']], acik_sinir(10), _yama)['mesru_kabul'], None, 'meşru vaka yoksa None')
raises(ValueError, ray_senaryo_olc, [], acik_sinir(10), _yama, msg='boş liste ValueError')

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
eq(ray_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(ray_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(ray_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(ray_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
eq(ray_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
raises(ValueError, ray_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, ray_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, ray_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, ray_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Meşru vakalarda `once_ok and not sonra_ok` koşuluyla `regresyon_n` sayacını artırmayı ve grup boşsa `None` döndürmeyi unutma.
```
:::

::: gorev 3 · İş gönderme şemasında kabuksuz `argv` ve ortam değişkeni sınırı kur
Kimliği doğrulanmış bir kullanıcının bile keyfi kabuk komutu veya dinamik bağlayıcı enjeksiyonu (`LD_PRELOAD` / `PYTHONPATH`) göndermesini kısıtlayan `komut_sinir_denetle(argv, ortam, izinli_betikler)` işlevini yaz:

- `argv`: boş olmayan `list[str]`; `ortam`: anahtar ve değerleri `str` olan `dict`; `izinli_betikler`: öğeleri `str` olan `set` veya `list`. Türler bozuksa `ValueError` fırlat.
- Güvenli kabul (`True`) koşulları:
  1. `argv[0] == 'python'` ve `len(argv) >= 2` ve `argv[1] in izinli_betikler` (`'-c'` veya izinli olmayan betik reddedilir);
  2. `argv` içindeki hiçbir argüman boş olmamalı ve kabuk/kontrol karakteri (`;`, `|`, `&`, `$`, `` ` ``, `>`, `<`, `\n`, `\r`, `\x00`) içermemeli;
  3. `ortam` sözlüğündeki anahtarlar tehlikeli yükleyici değişkenlerinden (`'LD_PRELOAD'`, `'LD_LIBRARY_PATH'`, `'PYTHONPATH'`, `'PYTHONSTARTUP'`, büyük/küçük harf duyarsız `upper()`) hiçbirini içermemeli.
- Dönüş: `bool`.

KUSURLU başlangıç `ortam` değişkenlerini ve `python -c` bayrağını kontrol etmediği için `PYTHONPATH` veya `argv` enjeksiyonunu geçiriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def komut_sinir_denetle(argv, ortam, izinli_betikler):
    return len(argv) >= 2 and argv[0] == 'python' and argv[1] in izinli_betikler
```

```solution
_YASAK_KAR = frozenset(';|&$`><\n\r\x00')
_YASAK_ENV = {'LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'PYTHONSTARTUP'}

def komut_sinir_denetle(argv, ortam, izinli_betikler):
    if (not isinstance(argv, list) or not argv or any(not isinstance(a, str) for a in argv)
            or not isinstance(ortam, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in ortam.items())
            or not isinstance(izinli_betikler, (set, list)) or any(not isinstance(b, str) for b in izinli_betikler)):
        raise ValueError('argv list[str], ortam dict[str,str], izinli_betikler set/list[str] olmali')
    if len(argv) < 2 or argv[0] != 'python' or argv[1] not in izinli_betikler:
        return False
    if any((not a) or any(c in _YASAK_KAR for c in a) for a in argv):
        return False
    if any(k.upper() in _YASAK_ENV for k in ortam):
        return False
    return True
```

```test
need('komut_sinir_denetle')
_izinli = {'egit.py', 'degerlendir.py'}
eq(komut_sinir_denetle(['python', 'egit.py', '--epoch', '5'], {'CUDA_VISIBLE_DEVICES': '0'}, _izinli), True, 'izinli betik ve temiz ortam geçmeli')

_kotu_cagrilar = [
    (['python', '-c', 'import os'], {}, _izinli),
    (['bash', 'egit.py'], {}, _izinli),
    (['python', ' baska.py'], {}, _izinli),
    (['python', 'egit.py', '5;id'], {}, _izinli),
    (['python', 'egit.py', '$(whoami)'], {}, _izinli),
    (['python', 'egit.py', ''], {}, _izinli),
    (['python', 'egit.py'], {'LD_PRELOAD': '/tmp/evil.so'}, _izinli),
    (['python', 'egit.py'], {'pythonpath': '/tmp'}, _izinli),
    (['python', 'egit.py'], {'PYTHONSTARTUP': '/tmp/init.py'}, _izinli),
    (['python'], {}, _izinli),
]
for _a, _e, _i in _kotu_cagrilar:
    eq(komut_sinir_denetle(_a, _e, _i), False, f'güvensiz iş komutu/ortamı reddedilmeli: {(_a, _e)!r}')

for _bozuk in (([], {}, _izinli), ('python egit.py', {}, _izinli), (['python', 'egit.py'], {'A': 1}, _izinli)):
    raises(ValueError, komut_sinir_denetle, *_bozuk, msg='şema dışı girdi ValueError')

eq(komut_sinir_denetle(['python', 'egit.py'], {}, ['egit.py']), True, 'argümansız izinli betik ve liste biçimli izin kümesi geçmeli')
# Her şema kuralı tek başına. Dikkat: izinli_betikler düz str olursa `in` alt dizge araması yapar
# ve 'egit.py' in 'egit.py' True olur; bu yüzden str kabul edilmez.
for _bozuk in (
    (['python', 'egit.py', 5], {}, _izinli),
    (['python', 'egit.py'], None, _izinli),
    (['python', 'egit.py'], [('A', 'b')], _izinli),
    (['python', 'egit.py'], {1: 'x'}, _izinli),
    (['python', 'egit.py'], {}, 'egit.py'),
    (['python', 'egit.py'], {}, {'egit.py', 5}),
):
    raises(ValueError, komut_sinir_denetle, *_bozuk, msg=f'şema dışı girdi ValueError: {_bozuk!r}')
```

```hint
Üç katmanı sırayla denetle: `argv[0] == 'python' and argv[1] in izinli_betikler`, tüm argümanlarda yasak karakter yokluğu ve `ortam` anahtarlarının `upper()` halinde `_YASAK_ENV` kümesinde bulunmaması.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay ve tartışma (15 sn).** "ShadowRay araştırması internete açık bırakılan Ray kümelerindeki kimliksiz iş gönderimini belgeledi; CVE-2023-48022 üreticinin kontrollü ağ tasarım varsayımı nedeniyle `DISPUTED` statüsündedir."
2. **Mimari ders (30 sn).** "Üreticinin ağ varsayımı ile sahadaki bulut dağıtımı çeliştiğinde yalnız ağ bölgesine güvenmek SSRF ve yatay hareket karşısında kırılır."
3. **Sınır ve ölçüm (30 sn).** "`job_izin` ile yönetim ağı şartına `kimlik_dogrulandi is True` ve `list[str]` üzerinde `'job-submit'` rolünü ekledim; senaryo koşusunda iç ağ sızıntısını `1.0`'dan `0.0`'a düşürdüm."
4. **En az ayrıcalık (25 sn).** "`komut_sinir_denetle` ile iş şemasını izinli betik listesine kilitledim ve `LD_PRELOAD`/`PYTHONPATH` ortam enjeksiyonunu engelledim."
5. **Kapanış (20 sn).** "AI altyapı yönetim uçları hem ağ yalıtımı hem uygulama katmanı kimlik/rol doğrulamasıyla çift kilitli çalışmalıdır."
:::

::: anlat Sınır ve kaynak
Bu dersteki model uygulama katmanı kimlik/RBAC ve şema doğrulamasını gösterir. Gerçek dağıtık eğitim kümelerinde çalışan işler aynı zamanda kapsayıcı izolasyonu, düğüm-üstü IAM rol kısıtlaması (IMDSv2 / iş bazlı hizmet hesabı) ve mTLS ile sınırlandırılmalıdır (`ai-savunma-13`).

- Birincil kaynaklar: [Oligo Security — ShadowRay: AI Workloads Actively Exploited in the Wild (Mart 2024)](https://www.oligo.security/blog/shadowray-attack-ai-workloads-actively-exploited-in-the-wild), [NVD CVE-2023-48022 kaydı (Disputed notu dahil)](https://nvd.nist.gov/vuln/detail/CVE-2023-48022). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Bir üreticinin dokümantasyona "Bu servis yalnız güvenilir iç ağda çalıştırılmalıdır" yazması ile servisin varsayılan olarak yerel geri döngü (`127.0.0.1`) ve zorunlu jeton (`token`) ile başlaması (`secure by default`) saha güvenliğini nasıl farklı etkiler?
:::

::: ozet
- Kontrollü ağ varsayımı, uygulama katmanı kimlik doğrulaması ve rol kontrolünün (`RBAC`) yerini tutmaz.
- `in` işleci dizgelerde alt dizge aradığı için rol listeleri mutlaka `isinstance(roller, list)` ile doğrulanır.
- İş gönderme uçlarında kabuksuz `argv` şeması ve `LD_PRELOAD`/`PYTHONPATH` ortam değişkeni filtresi savunma derinliği sağlar.
:::
