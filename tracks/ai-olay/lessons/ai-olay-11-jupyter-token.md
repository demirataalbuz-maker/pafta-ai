---
id: ai-olay-11
title: "Jupyter Yanlış Yapılandırma · Ağ Dinleme, Jeton ve TLS Denetimi"
summary: Resmi Jupyter Server güvenlik belgelerine dayanarak açık ağ dinleme (0.0.0.0/::), kimlik doğrulamasız çalıştırma ve TLS eksikliğini denetle, ölç ve güvenli varsayılana dönüştür.
esleme: ai-savunma-01, ai-savunma-05, ai-savunma-15, ai-savunma-25
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Veri bilimi ve model geliştirme ortamlarında **Jupyter Server / Notebook** etkileşimli Python çekirdeği (`kernel`) sunduğu için tarayıcıdan erişebilen herkes doğrudan işletim sistemi kullanıcısının yetkisiyle kod çalıştırabilir. **Jupyter Server resmi güvenlik dokümantasyonu**, sunucunun varsayılan olarak yalnız yerel geri döngüde (`127.0.0.1` / `localhost`) ve tek kullanımlık jeton (`token`) ile başladığını; buna karşılık konteyner veya bulut sanal makinelerinde `--ip=0.0.0.0 --ServerApp.token=''` gibi bayraklarla korumasız dış ağa açılmasının doğrudan yetkisiz kod yürütmeye yol açtığını açıkça belgeler.

> [!NOTE]
> **Kaynak dürüstlüğü:** Bu derste doğrulanmamış tekil bir kripto-madencilik kampanyası hikâyesi uydurulmaz; doğrudan resmi Jupyter operatör güvenlik kılavuzundaki yapılandırma kuralları yerel ve çevrimdışı Python denetçisi olarak modellenir.
:::

::: anlat 2. Mekanizma · geliştirici kolaylığı bayrakları nasıl tam kabuk erişimine dönüşür?
Docker içinde Jupyter başlatan bir geliştirici dışarıdan bağlanabilmek için `bind='0.0.0.0'` ayarlar, kopyala-yapıştır jetonundan kurtulmak için `token=''` yapar ve sertifika uğraşı olmasın diye `tls=False` bırakır (`ai-savunma-05`, `ai-savunma-15`). Bu üç karar üç ayrı güvenlik bulgusu üretir:

1. **`'public-listen'`:** `bind` adresi `'127.0.0.1'` veya `'localhost'` dışında bir değerse (`'0.0.0.0'`, `'::'`, `'*'`, dış IP) servis ağ üzerinden erişilebilirdir.
2. **`'no-auth'`:** Hem `token` boş hem `password` boş **ve** önünde doğrulanmış bir ters vekil (`proxy_auth is True`) yoksa kimlik doğrulama kapalıdır (yerelde bile başka yerel süreçler veya tarayıcı DNS yeniden bağlama saldırıları erişebilir!).
3. **`'no-tls'`:** Servis ağa açıkken (`public-listen`) `tls is True` değilse gönderilen jeton veya parola ağ üzerinde açık metin akar.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız `bind == '0.0.0.0'` değerini açık ağ saymak | IPv6 tüm arayüzler (`'::'`), `'*'` veya makinenin dış IP adresini yerel sanır | `bind not in ('127.0.0.1', 'localhost')` kontrolü |
| `if not cfg.get('proxy_auth'):` ile gevşek kontrol | `proxy_auth: 1` veya `'evet'` gibi bozuk yapılandırma değerlerini kimlik doğrulama sayar | `cfg.get('proxy_auth') is True` |
| `token: '   '` (yalnız boşluk) değerini geçerli jeton saymak | Boşluk dizgesi gerçek bir sır değildir | `isinstance(val, str) and bool(val.strip())` kontrolü |
:::

::: tahmin IPv6 `'::'` ve sayısal `proxy_auth: 1` ayarları zayıf denetçiden nasıl kaçar?
Aşağıdaki iki yapılandırmayı yalnız `'0.0.0.0'` arayan zayıf denetçi ile tam denetçi nasıl değerlendirir?

```python
ayar = {'bind': '::', 'token': '', 'proxy_auth': 1, 'tls': False}

zayif_acik_ag = (ayar['bind'] == '0.0.0.0')
tam_acik_ag = (ayar['bind'] not in ('127.0.0.1', 'localhost'))
tam_kimlik_var = bool(ayar.get('token', '').strip()) or (ayar.get('proxy_auth') is True)
print('zayıf açık ağ:', zayif_acik_ag, '| tam açık ağ:', tam_acik_ag)
print('tam kimlik doğrulama var mı:', tam_kimlik_var)
```

???

```cikti
zayıf açık ağ: False | tam açık ağ: True
tam kimlik doğrulama var mı: False
```
IPv6 `'::'` tüm ağ arayüzlerini dinlediği halde yalnız `'0.0.0.0'` arayan denetçiden temiz geçer; `proxy_auth: 1` ise `is True` kontrolü yoksa kimlik doğrulama var sanılır.
:::

::: gorev 1 · Yapılandırma denetçisini (`notebook_bulgulari`) kur
`notebook_bulgulari(cfg)` işlevini yaz:

- `cfg` bir `dict` değilse `ValueError` fırlat.
- Varsayılanlar: `bind` yoksa `'127.0.0.1'`; `token` ve `password` yoksa `''`. (`bind` mevcutsa boş olmayan `str` olmalı, `token` ve `password` mevcutsa `str` olmalı; aksi halde `ValueError` fırlat.)
- Bulguları **tam şu sırayla** kontrol edip listeye ekle:
  1. `'public-listen'`: etkin `bind` değeri `('127.0.0.1', 'localhost')` dışında ise;
  2. `'no-auth'`: etkin `token.strip()` boş **ve** etkin `password.strip()` boş **ve** `cfg.get('proxy_auth') is not True` ise;
  3. `'no-tls'`: `'public-listen'` bulgusu varsa **ve** `cfg.get('tls') is not True` ise.
- Dönüş: bulgu dizgelerinin listesi (`list[str]`; güvenli yapılandırmada `[]`). Girdi sözlüğünü değiştirme.

KUSURLU başlangıç yalnız `bind == '0.0.0.0'` ve boş `token` birleşimine bakıyor; `password`, `'localhost'`, `'::'`, `'no-auth'` ve `'no-tls'` kurallarını kaçırıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  {\n    "bind": "0.0.0.0",\n    "token": "",\n    "tls": false\n  }\n]', encoding='utf-8')
```

```starter
def notebook_bulgulari(cfg):
    if cfg.get('bind') == '0.0.0.0' and not cfg.get('token'):
        return ['public-listen']
    return []

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(notebook_bulgulari(*_args))
```

```solution
def notebook_bulgulari(cfg):
    if not isinstance(cfg, dict):
        raise ValueError('cfg dict olmali')
    bind = cfg.get('bind', '127.0.0.1')
    token = cfg.get('token', '')
    password = cfg.get('password', '')
    if not isinstance(bind, str) or not bind.strip() or not isinstance(token, str) or not isinstance(password, str):
        raise ValueError('bind bos olmayan str, token ve password str olmali')
    bulgular = []
    acik_ag = bind not in ('127.0.0.1', 'localhost')
    if acik_ag:
        bulgular.append('public-listen')
    if not token.strip() and not password.strip() and cfg.get('proxy_auth') is not True:
        bulgular.append('no-auth')
    if acik_ag and cfg.get('tls') is not True:
        bulgular.append('no-tls')
    return bulgular

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(notebook_bulgulari(*_args))
```

```test
need('notebook_bulgulari')
import copy

_ornek = {'bind': '0.0.0.0', 'token': '', 'tls': False}
_yedek = copy.deepcopy(_ornek)
eq(notebook_bulgulari(_ornek), ['public-listen', 'no-auth', 'no-tls'], 'üç bulgu doğru sırayla dönmeli')
eq(_ornek, _yedek, 'girdi değişmemeli')

eq(notebook_bulgulari({'bind': '127.0.0.1', 'token': 'gizli-jeton'}), [], 'yerel + jetonlu yapılandırma temiz')
eq(notebook_bulgulari({'bind': 'localhost', 'password': 'hashed-password'}), [], 'localhost + parolalı yapılandırma temiz')
eq(notebook_bulgulari({'proxy_auth': True}), [], 'varsayılan 127.0.0.1 + proxy_auth=True temiz')
eq(notebook_bulgulari({}), ['no-auth'], 'boş sözlükte varsayılan yerel ama kimliksiz -> yalnız no-auth')
eq(notebook_bulgulari({'bind': '127.0.0.1', 'token': '   '}), ['no-auth'], 'yalnız boşluktan oluşan token geçersizdir')
eq(notebook_bulgulari({'bind': '127.0.0.1', 'proxy_auth': 1}), ['no-auth'], 'proxy_auth=1 True sayılmaz')
eq(notebook_bulgulari({'bind': '::', 'token': 'tok', 'tls': True}), ['public-listen'], 'IPv6 :: TLS olsa da public-listen üretmeli')
eq(notebook_bulgulari({'bind': '0.0.0.0', 'token': 'tok', 'tls': 1}), ['public-listen', 'no-tls'], 'tls=1 True sayılmaz')

for _bozuk in (None, [], 'cfg', {'bind': ''}, {'bind': 127}, {'token': 123}, {'password': None}):
    raises(ValueError, notebook_bulgulari, _bozuk, msg='bozuk cfg veya alan tipi ValueError fırlatmalı')
```

```hint
`bind` için `'127.0.0.1'` ve `'localhost'` dışındaki her adresi `acik_ag = True` işaretle; `token.strip()` ve `password.strip()` boşsa ve `proxy_auth is not True` ise `'no-auth'`, `acik_ag and tls is not True` ise `'no-tls'` ekle.
```
:::

::: gorev 2 · Açık ve yamalı yapılandırma kapısını senaryo vakalarında ölç
CI dağıtım kapısı yalnız `bulgular == []` olduğunda konteynerin başlatılmasına izin verir! `notebook_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (cfg,), ...}` sözlüğüdür (`saldiri=True` güvensiz yapılandırma, `saldiri=False` güvenli yerel yapılandırma). Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Sınır işlevi **boş liste (`sonuc == []`)** döndürdüğünde yapılandırmaya **başlatma izni verildi** sayılır!
- Güvensiz vakada (`saldiri is True`) `sonuc == []` dönmesi **riskli servisin yayına kaçması (`sizma`)**; güvenli vakada (`saldiri is False`) `sonuc == []` dönmesi **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `sonuc == []` yerine `bool(sonuc)` kontrolü yaptığı için bulgu listesi dolu olduğunda izin verilmiş sanarak tüm oranları ters çeviriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def notebook_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if bool(acik_fn(*v['girdi']))) / len(s), 4) if s else None,
        'sonra_sizma': round(sum(1 for v in s if bool(yamali_fn(*v['girdi']))) / len(s), 4) if s else None,
        'mesru_kabul': round(sum(1 for v in m if bool(yamali_fn(*v['girdi']))) / len(m), 4) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def notebook_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('bozuk vaka semasi')
        once_izin = (acik_fn(*copy.deepcopy(v['girdi'])) == [])
        sonra_izin = (yamali_fn(*copy.deepcopy(v['girdi'])) == [])
        if v['saldiri']:
            s_n += 1
            s_once += int(once_izin)
            s_sonra += int(sonra_izin)
        else:
            m_n += 1
            m_sonra += int(sonra_izin)
            if once_izin and not sonra_izin:
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
need('notebook_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(cfg):
    out = []
    pub = cfg.get('bind', '127.0.0.1') not in ('127.0.0.1', 'localhost')
    if pub:
        out.append('public-listen')
    if not cfg.get('token', '').strip() and not cfg.get('password', '').strip() and cfg.get('proxy_auth') is not True:
        out.append('no-auth')
    if pub and cfg.get('tls') is not True:
        out.append('no-tls')
    return out

_vakalar = senaryo_vakalari(11, tohum=11)
eq(notebook_senaryo_olc(_vakalar, acik_sinir(11), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık denetçi 4 riskli ayarı da [] döndürerek kaçırır (1.0), tam denetçi hepsinde bulgu üretir (0.0)')

eq(notebook_senaryo_olc(_vakalar, acik_sinir(11), lambda _c: ['her-zaman-engel'])['regresyon_n'], 2, 'her ayara bulgu üreten denetçi 2 meşru vakayı bozar')
raises(ValueError, notebook_senaryo_olc, [], acik_sinir(11), _yama, msg='boş liste ValueError')

# Ölçüm mantığı alandan bağımsızdır: denetçi boş bulgu listesi ([]) döndürürse ayar "geçti" sayılır.
_el = [
    {'saldiri': True, 'girdi': ('s-ikisi-gecer',)},
    {'saldiri': True, 'girdi': ('s-acik-de-durdurur',)},
    {'saldiri': True, 'girdi': ('s-yalniz-acik-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-durdurur',)},
    {'saldiri': False, 'girdi': ('m-regresyon',)},
]
def _sinir(gecenler):
    return lambda c: [] if c in gecenler else ['bulgu']
_acik_el = _sinir(('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon'))
_yama_el = _sinir(('s-ikisi-gecer', 'm-ikisi-gecer'))
eq(notebook_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(notebook_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(notebook_senaryo_olc(_el, _sinir(()), _sinir(()))['regresyon_n'], 0, 'açık denetçinin de bulgu ürettiği meşru vaka regresyon sayılmaz')
eq(notebook_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
eq(notebook_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
for _tuhaf in (lambda _c: None, lambda _c: (), lambda _c: ''):
    eq(notebook_senaryo_olc(_el, _tuhaf, _tuhaf)['once_sizma'], 0.0, 'yalnız boş liste "bulgu yok" sayılır')
raises(ValueError, notebook_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, notebook_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, notebook_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, notebook_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Dağıtım kapısı yalnız sıfır bulguda (`sonuc == []`) açılır; dolayısıyla `once_izin = (acik_fn(...) == [])` ve `sonra_izin = (yamali_fn(...) == [])` olmalıdır!
```
:::

::: gorev 3 · Güvensiz yapılandırmayı güvenli varsayılana (`secure baseline`) dönüştür
Otomatik sertleştirme aracı `guvenli_notebook_ayari(cfg, uretilen_token)` işlevini yaz:

- `cfg` bir `dict`, `uretilen_token` ise en az `16` karakterlik boşluksuz `str` olmalı; aksi halde `ValueError` fırlat.
- Girdi `cfg` sözlüğünü **değiştirmeden** yeni bir kopya sözlük hazırla (`degisenler` listesini alfabetik sırala):
  1. `bind` alanı `'127.0.0.1'` veya `'localhost'` değilse (veya eksikse) `'bind'` değerini `'127.0.0.1'` yap (mevcut değer `'127.0.0.1'`/`'localhost'` dışında idiyse veya eksikse `'bind'` alanını değişenlere yalnız değer gerçekten değiştiyse veya eklendiyse ekle: yani `yeni.get('bind') != cfg.get('bind')`).
  2. Mevcut `token` (dolu `str`), `password` (dolu `str`) veya `proxy_auth is True` üçlüsünden **hiçbiri** yoksa `yeni['token'] = uretilen_token` ata.
  3. `allow_root` alanı `False` değilse `yeni['allow_root'] = False` ata.
- `degisen_alanlar`: `sorted(k for k in yeni if k not in cfg or yeni[k] != cfg[k])`.
- Dönüş: `{'ayar': yeni, 'degisen_alanlar': degisen_alanlar}`.

KUSURLU başlangıç mevcut geçerli parolayı ezip üzerine `uretilen_token` yazıyor ve `cfg` sözlüğünü yerinde değiştiriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def guvenli_notebook_ayari(cfg, uretilen_token):
    cfg['bind'] = '127.0.0.1'
    cfg['token'] = uretilen_token
    cfg['allow_root'] = False
    return {'ayar': cfg, 'degisen_alanlar': ['allow_root', 'bind', 'token']}
```

```solution
import copy

def guvenli_notebook_ayari(cfg, uretilen_token):
    if not isinstance(cfg, dict) or not isinstance(uretilen_token, str) or len(uretilen_token) < 16 or any(c.isspace() for c in uretilen_token):
        raise ValueError('cfg dict ve uretilen_token >=16 karakterlik bosluksuz str olmali')
    yeni = copy.deepcopy(cfg)
    mevcut_bind = yeni.get('bind')
    if mevcut_bind not in ('127.0.0.1', 'localhost'):
        yeni['bind'] = '127.0.0.1'
    tok_var = isinstance(yeni.get('token'), str) and bool(yeni['token'].strip())
    pw_var = isinstance(yeni.get('password'), str) and bool(yeni['password'].strip())
    proxy_var = yeni.get('proxy_auth') is True
    if not (tok_var or pw_var or proxy_var):
        yeni['token'] = uretilen_token
    if yeni.get('allow_root') is not False:
        yeni['allow_root'] = False
    degisen = sorted(k for k in yeni if k not in cfg or yeni[k] != cfg[k] or type(yeni[k]) is not type(cfg[k]))
    return {'ayar': yeni, 'degisen_alanlar': degisen}
```

```test
need('guvenli_notebook_ayari')
import copy

_acik = {'bind': '0.0.0.0', 'token': '', 'allow_root': True}
_yedek = copy.deepcopy(_acik)
_sonuc = guvenli_notebook_ayari(_acik, '0123456789abcdef0123')
eq(_acik, _yedek, 'orijinal sözlük değişmemeli')
eq(_sonuc, {
    'ayar': {'bind': '127.0.0.1', 'token': '0123456789abcdef0123', 'allow_root': False},
    'degisen_alanlar': ['allow_root', 'bind', 'token'],
}, 'üç güvensiz alan sertleştirilmeli')

_parolali = {'bind': 'localhost', 'password': 'argon2:$argon2id$hash', 'allow_root': False}
eq(guvenli_notebook_ayari(_parolali, '0123456789abcdef0123'), {
    'ayar': _parolali,
    'degisen_alanlar': [],
}, 'zaten güvenli olan localhost + password ayarına dokunulmamalı')

eq(guvenli_notebook_ayari({'bind': '127.0.0.1', 'token': 'mevcut-uzun-anahtar', 'allow_root': 0}, '0123456789abcdef0123')['degisen_alanlar'], ['allow_root'], 'allow_root=0 int olduğu için gerçek False değerine çevrilmeli')

for _bozuk in ((None, '0123456789abcdef'), ({}, 'kisa'), ({}, 'bosluk var 12345678'),
               ({}, '0123456789abcde'), ({}, None), ({}, b'0123456789abcdef')):
    raises(ValueError, guvenli_notebook_ayari, *_bozuk, msg=f'kısa/boşluklu/str olmayan token veya bozuk cfg ValueError: {_bozuk[1]!r}')

_tok16 = '0123456789abcdef'
eq(guvenli_notebook_ayari({'bind': 'localhost', 'allow_root': False}, _tok16)['ayar']['token'], _tok16, 'tam 16 karakterlik token kabul edilir')
eq(guvenli_notebook_ayari({'bind': 'localhost', 'password': '   ', 'allow_root': False}, _tok16), {
    'ayar': {'bind': 'localhost', 'password': '   ', 'allow_root': False, 'token': _tok16},
    'degisen_alanlar': ['token'],
}, 'yalnız boşluktan oluşan parola kimlik doğrulama sayılmaz; token eklenir')
eq(guvenli_notebook_ayari({'bind': 'localhost', 'proxy_auth': True, 'allow_root': False}, _tok16), {
    'ayar': {'bind': 'localhost', 'proxy_auth': True, 'allow_root': False},
    'degisen_alanlar': [],
}, 'proxy_auth=True ile kimlik doğrulama vekilde; token eklenmez')
eq(guvenli_notebook_ayari({'bind': '127.0.0.1', 'token': 'mevcut-uzun-anahtar'}, _tok16), {
    'ayar': {'bind': '127.0.0.1', 'token': 'mevcut-uzun-anahtar', 'allow_root': False},
    'degisen_alanlar': ['allow_root'],
}, 'cfg içinde hiç olmayan allow_root eklenir ve değişen alan sayılır')
```

```hint
Önce `yeni = copy.deepcopy(cfg)` al; kimlik doğrulama üçlüsünden (`tok_var or pw_var or proxy_var`) biri bile sağlamsa mevcut kimlik ayarına dokunma; sonda hem değer hem tip (`0` vs `False`) farkını kontrol ederek `degisen_alanlar` listesini üret.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kaynak sınırı (15 sn).** "Doğrulanmamış kampanya söylentileri yerine doğrudan resmi Jupyter Server güvenlik kılavuzundaki yapılandırma sözleşmesini temel aldım."
2. **Üç kritik bulgu (30 sn).** "Etkileşimli Python çekirdeği doğrudan kod çalıştırdığı için `0.0.0.0`/`::` açık ağ dinlemesi (`public-listen`), boş jeton/parola (`no-auth`) ve şifresiz açık ağ (`no-tls`) birlikte denetlenir."
3. **Ölçüm tuzağı (30 sn).** "Dağıtım kapısı yalnız sıfır bulguda (`[]`) açılır; senaryo koşusunda zayıf denetçinin kaçırdığı 4 riskli ayarın tamamı `notebook_bulgulari` ile durduruldu."
4. **Otomatik sertleştirme (25 sn).** "`guvenli_notebook_ayari` ile meşru `localhost` ve mevcut parolaları bozmadan açık portları `127.0.0.1`, `allow_root=False` ve güçlü jeton tabanına çektim."
5. **Kapanış (20 sn).** "Geliştirme araçlarının konteyner imajlarında kolaylık bayrakları üretim ortamına taşınmadan önce CI politika kapısıyla taranmalıdır."
:::

::: anlat Sınır ve kaynak
Bu derste Jupyter sunucu yapılandırma sözlüğü denetlenir. Uzaktan erişimin iş gereksinimi olduğu kurumsal ortamlarda Jupyter doğrudan internete açılmaz; SSH tüneli, mTLS veya kimlik sağlayıcı doğrulamalı ters vekil (`JupyterHub` / OAuth proxy) arkasında çalıştırılır (`ai-savunma-05`).

- Birincil kaynak: [Jupyter Server Documentation — Security in the Jupyter Server](https://jupyter-server.readthedocs.io/en/latest/operators/security.html). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Yalnız `127.0.0.1` üzerinde dinleyen ama `token=''` (kimlik doğrulamasız) bırakılan bir Jupyter sunucusu, geliştirici aynı makinedeki tarayıcıda kötücül bir web sayfasını ziyaret ettiğinde neden hâlâ risk altındadır (`DNS rebinding` / `CSRF`)?
:::

::: ozet
- Etkileşimli not defteri sunucuları tasarım gereği kod yürütme ucu olduğu için ağ ve kimlik sınırları hayati önemdedir.
- `'127.0.0.1'` ve `'localhost'` dışındaki tüm bağlamalar (`'::'`, `'0.0.0.0'`) açık ağ kabul edilir; boşluktan ibaret jetonlar geçerli sır sayılmaz.
- CI dağıtım kapılarında boş bulgu listesi (`[]`) ile dolu bulgu listesi ayrımı açıkça ölçülür.
:::
