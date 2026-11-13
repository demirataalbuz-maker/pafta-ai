---
id: ai-bulut-04
title: "Vertex ve Azure OpenAI · Hizmet Kimliği"
summary: Model çağrısında statik API anahtarı yerine yönetilen hizmet kimliği kullanmanın mantığını kur; doğrulanmış token iddialarını (aud, sub, exp, nbf, scope) sözleşmeye göre denetle.
esleme: ai-savunma-15, ai-temel-16, ai-bulut-02, ai-bulut-07
timeout: 30
---

::: anlat 1. Statik anahtardan hizmet kimliğine
Bir uygulamanın bulutta bir modeli çağırmasının iki yolu vardır:

1. **Statik API anahtarı.** Uzun ömürlü bir dizge; kim taşıyorsa o çağırır. Kod deposuna, ortam değişkenine ya da bir yapılandırma dosyasına sızdığında kimin kullandığını ayırt etmek zordur ve döndürülene kadar geçerlidir.
2. **Hizmet kimliği.** Uygulama, platformun verdiği bir kimlikle (Azure'da *managed identity*, Google Cloud'da *service account*) kısa ömürlü bir token alır ve rolüne bağlı izinlerle çağırır.

Microsoft'un Azure OpenAI belgesi Entra ID ile kimlik doğrulamayı, kaynağı *"without storing an API key"* çağırmanın yolu olarak anlatır ve çağıran kimliğe `Cognitive Services OpenAI User` rolünün verilmesini gösterir. Google Cloud'un Vertex AI erişim denetimi belgesi de aynı kalıbı IAM rolleri ve hizmet hesaplarıyla kurar. İki platformda da güvenlik kararı aynı yere taşınır: **token kimin adına, kime, hangi süre ve hangi kapsamla verildi?**

> [!NOTE]
> Bu derste token çözülmez ve imza doğrulanmaz. `verified` alanı, imzayı platformun (güvenilir host) doğruladığını bildiren sentetik bir bayraktır. Gerçek token, anahtar ya da ağ çağrısı yoktur.
:::

::: anlat 2. Mekanizma: imzası doğru token neden yine de reddedilir?
İmza doğrulaması yalnız token'ı kimin **ürettiğini** kanıtlar. Token'ın **bu istek için** geçerli olup olmadığı iddialardan (*claims*) okunur. RFC 7519 bu iddiaları tanımlar:

- **`aud` (bölüm 4.1.3):** token kime yönelik? Tek bir dizge ya da dizge listesi olabilir. Başka bir hizmet için alınmış geçerli bir token bu hizmete gösterilirse (*token yeniden kullanımı*) reddedilmelidir.
- **`sub` (4.1.2):** token kimin adına?
- **`exp` (4.1.4):** RFC'ye göre şimdiki zaman bu değerden **önce** olmalıdır; `exp == now` artık geçersizdir.
- **`nbf` (4.1.5):** varsa, şimdiki zaman bu değerden önce olamaz.

`scope` ise RFC 7519'da tanımlı değildir. Platforma özgü yetki listesini temsil eden bu dersteki sentetik alandır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "İmza geçerliyse kabul" | Başka hizmete verilmiş token bu hizmette de çalışır | `aud` bu hizmeti içermeli |
| `aud`'u yalnız dizge sanmak | RFC'ye göre liste olabilir; liste gelince ya hepsi reddedilir ya da `==` hiç eşleşmez | Dizge → eşitlik, liste → üyelik |
| `exp >= now` | Süresi tam şimdi dolan token kabul edilir | `exp > now` |
| `nbf`'yi yok saymak | Henüz geçerli olmayan token kullanılır | `nbf` varsa `nbf <= now` |
| `True` yerine doğru değer kontrolü | `verified = 1` ya da `'true'` güvenilir host kararı değildir | `verified is True` |
:::

::: tahmin Süresi tam şimdi dolan token
`exp` ile `now` eşit olduğunda iki farklı karşılaştırma ne söyler?

```python
now = 1_700_000_000
exp = 1_700_000_000
print('exp >= now:', exp >= now)
print('exp > now :', exp > now)
```

???

```cikti
exp >= now: True
exp > now : False
```
RFC 7519 bölüm 4.1.4'e göre şimdiki zaman `exp`'ten önce olmalıdır. Eşitlik bu koşulu sağlamaz; `>=` kullanan bir kontrol süresi dolmuş token'ı bir saniye daha kabul eder.
:::

::: gorev 1 · Doğrulanmış token iddialarını denetle
`kimlik_izin(claims, now, audience, subject)` işlevini yaz. Aşağıdaki koşulların **tamamı** sağlanırsa `True`, aksi halde `False` döndür; hata fırlatma.

- `claims` bir `dict`; `now` `bool` olmayan bir `int`; `audience` ve `subject` boş olmayan `str`.
- `claims['verified'] is True`.
- `aud`: `str` ise `audience`'a eşit; `list` ise öğelerinin hepsi `str` ve `audience` listede. Başka türler reddedilir.
- `claims['sub'] == subject` ve `sub` bir `str`.
- `exp` `bool` olmayan bir `int` ve `exp > now`.
- `nbf` **varsa** `bool` olmayan bir `int` ve `nbf <= now`.
- `scope` bir `list`, öğelerinin hepsi `str` ve `'invoke'` listede.

KUSURLU başlangıç `verified`'ın doğruluğuna bakıyor, `aud`'u yalnız `==` ile karşılaştırıyor, `exp >= now` kullanıyor ve `nbf`'yi yok sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[{"verified": true, "aud": ["model-api", "gunluk-api"], "sub": "uygulama-a", "exp": 1700000600, "nbf": 1699999990, "scope": ["invoke"]}, 1700000000, "model-api", "uygulama-a"]', encoding='utf-8')
```

```starter
def kimlik_izin(claims, now, audience, subject):
    return bool(
        claims.get('verified')
        and claims.get('aud') == audience
        and claims.get('sub') == subject
        and claims.get('exp', 0) >= now
        and 'invoke' in claims.get('scope', [])
    )

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(kimlik_izin(*_args))
```

```solution
def _tam_sayi(x):
    return type(x) is int

def kimlik_izin(claims, now, audience, subject):
    if (not isinstance(claims, dict) or not _tam_sayi(now)
            or not isinstance(audience, str) or not audience
            or not isinstance(subject, str) or not subject):
        return False
    if claims.get('verified') is not True:
        return False
    aud = claims.get('aud')
    if isinstance(aud, str):
        aud_ok = aud == audience
    elif isinstance(aud, list):
        aud_ok = all(isinstance(a, str) for a in aud) and audience in aud
    else:
        aud_ok = False
    if not aud_ok:
        return False
    if not isinstance(claims.get('sub'), str) or claims['sub'] != subject:
        return False
    exp = claims.get('exp')
    if not _tam_sayi(exp) or not exp > now:
        return False
    if 'nbf' in claims and (not _tam_sayi(claims['nbf']) or claims['nbf'] > now):
        return False
    scope = claims.get('scope')
    return isinstance(scope, list) and all(isinstance(s, str) for s in scope) and 'invoke' in scope

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(kimlik_izin(*_args))
```

```test
need('kimlik_izin')
import copy
_N = 1_700_000_000
_iyi = {'verified': True, 'aud': 'model-api', 'sub': 'uygulama-a', 'exp': _N + 600, 'scope': ['invoke', 'list']}
_yedek = copy.deepcopy(_iyi)
eq(kimlik_izin(_iyi, _N, 'model-api', 'uygulama-a'), True, 'tam ve geçerli iddialar kabul')
eq(_iyi, _yedek, 'claims değişmemeli')
eq(kimlik_izin(dict(_iyi, aud=['gunluk-api', 'model-api']), _N, 'model-api', 'uygulama-a'), True, 'liste aud içinde bu hizmet varsa kabul')
eq(kimlik_izin(dict(_iyi, exp=_N + 1), _N, 'model-api', 'uygulama-a'), True, 'bir saniye kalan token geçerli')
eq(kimlik_izin(dict(_iyi, nbf=_N), _N, 'model-api', 'uygulama-a'), True, 'nbf == now geçerli')
eq(kimlik_izin(dict(_iyi, nbf=_N - 5), _N, 'model-api', 'uygulama-a'), True, 'nbf geçmişte geçerli')

_red = [
    (dict(_iyi, verified=1), 'verified 1 güvenilir değil'),
    (dict(_iyi, verified='true'), 'verified dizge güvenilir değil'),
    ({k: v for k, v in _iyi.items() if k != 'verified'}, 'verified yok'),
    (dict(_iyi, aud='gunluk-api'), 'başka hizmete verilmiş token'),
    (dict(_iyi, aud=['gunluk-api']), 'liste aud bu hizmeti içermiyor'),
    (dict(_iyi, aud=['model-api', 5]), 'liste aud içinde str olmayan öğe'),
    (dict(_iyi, aud=('model-api',)), 'tuple aud desteklenmez'),
    (dict(_iyi, aud=None), 'aud yok'),
    (dict(_iyi, sub='uygulama-b'), 'başka konu'),
    (dict(_iyi, sub=None), 'sub None'),
    ({k: v for k, v in _iyi.items() if k != 'sub'}, 'sub anahtarı yok'),
    (dict(_iyi, exp=_N), 'exp == now süresi dolmuş'),
    (dict(_iyi, exp=_N - 1), 'exp geçmişte'),
    (dict(_iyi, exp=float(_N + 600)), 'float exp'),
    (dict(_iyi, exp=True), 'bool exp'),
    (dict(_iyi, nbf=_N + 1), 'henüz geçerli değil'),
    (dict(_iyi, nbf=float(_N)), 'float nbf'),
    (dict(_iyi, nbf=None), 'nbf var ama int değil'),
    (dict(_iyi, scope=['list']), 'invoke kapsamı yok'),
    (dict(_iyi, scope='invoke'), 'scope liste değil'),
    (dict(_iyi, scope=['invoke', 7]), 'scope içinde str olmayan öğe'),
]
for _c, _neden in _red:
    eq(kimlik_izin(_c, _N, 'model-api', 'uygulama-a'), False, f'reddedilmeli: {_neden}')
for _arg in ((None, _N, 'model-api', 'uygulama-a'), (_iyi, True, 'model-api', 'uygulama-a'),
             (_iyi, float(_N), 'model-api', 'uygulama-a'), (_iyi, _N, '', 'uygulama-a'),
             (_iyi, _N, None, 'uygulama-a'), (_iyi, _N, 'model-api', ''), (_iyi, _N, 'model-api', 5)):
    eq(kimlik_izin(*_arg), False, f'bozuk üst argüman False dönmeli: {_arg[1:]!r}')
eq(kimlik_izin(dict(_iyi, aud=''), _N, '', 'uygulama-a'), False, 'boş audience ile boş aud eşleşmez')
eq(kimlik_izin(dict(_iyi, sub=''), _N, 'model-api', ''), False, 'boş subject ile boş sub eşleşmez')
```

```hint
Her iddiayı ayrı bir erken dönüşle yaz. `aud` için önce türüne bak: dizge ise `==`, liste ise önce bütün öğelerin dizge olduğunu doğrula, sonra `in`.
```
:::

::: gorev 2 · Uygulamaların kimlik biçimini ve rollerini denetle
`kimlik_envanteri(servisler)` işlevini yaz. Her servis `{'ad': str, 'kimlik': 'yonetilen' | 'anahtar', 'anahtar_kodda': bool, 'roller': list[str]}`.

- `servisler` `list` değilse; bir servis `dict` değilse; `ad` boş olmayan `str` değilse ya da tekrar ediyorsa; `kimlik` bu iki değerden biri değilse; `anahtar_kodda` `bool` değilse; `roller` `str` listesi değilse `ValueError`.
- Her servis için bulgular, bu sırayla:
  1. `kimlik == 'anahtar'` → `'statik-anahtar'`;
  2. `anahtar_kodda is True` → `'koda-gomulu-anahtar'` (kimlik türünden bağımsız: yönetilen kimliğe geçilmiş ama eski anahtar kodda kalmış olabilir);
  3. `kimlik == 'yonetilen'` ve `roller` boş → `'rol-yok'`;
  4. `roller` içinde `'Cognitive Services OpenAI User'` dışında herhangi bir rol varsa → `'genis-rol'`.
- Dönüş: yalnız bulgusu olan servisler için `{ad: [bulgular]}`.

KUSURLU başlangıç yalnız kimlik türüne bakıyor: yönetilen kimliğe geçmiş ama anahtarı kodda bırakmış servisi ve geniş rolü kaçırıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def kimlik_envanteri(servisler):
    sonuc = {}
    for s in servisler:
        if s['kimlik'] == 'anahtar':
            sonuc[s['ad']] = ['statik-anahtar']
    return sonuc
```

```solution
_DAR_ROL = 'Cognitive Services OpenAI User'

def kimlik_envanteri(servisler):
    if not isinstance(servisler, list):
        raise ValueError('servisler list olmali')
    gorulen = set()
    sonuc = {}
    for s in servisler:
        if (not isinstance(s, dict) or not isinstance(s.get('ad'), str) or not s['ad'].strip()
                or s.get('kimlik') not in ('yonetilen', 'anahtar') or type(s.get('anahtar_kodda')) is not bool
                or not isinstance(s.get('roller'), list) or any(not isinstance(r, str) for r in s['roller'])):
            raise ValueError('bozuk servis kaydi')
        if s['ad'] in gorulen:
            raise ValueError('yinelenen servis adi')
        gorulen.add(s['ad'])
        bulgu = []
        if s['kimlik'] == 'anahtar':
            bulgu.append('statik-anahtar')
        if s['anahtar_kodda']:
            bulgu.append('koda-gomulu-anahtar')
        if s['kimlik'] == 'yonetilen' and not s['roller']:
            bulgu.append('rol-yok')
        if any(r != _DAR_ROL for r in s['roller']):
            bulgu.append('genis-rol')
        if bulgu:
            sonuc[s['ad']] = bulgu
    return sonuc
```

```test
need('kimlik_envanteri')
import copy
_U = 'Cognitive Services OpenAI User'
def _s(ad, kimlik='yonetilen', kodda=False, roller=None):
    return {'ad': ad, 'kimlik': kimlik, 'anahtar_kodda': kodda, 'roller': [_U] if roller is None else roller}
_env = [
    _s('ozetleyici'),
    _s('eski-bot', kimlik='anahtar', kodda=True, roller=[]),
    _s('gecis-yarim', kodda=True),
    _s('yeni-servis', roller=[]),
    _s('yonetim-paneli', roller=[_U, 'Owner']),
    _s('anahtarli-ama-temiz-kod', kimlik='anahtar', roller=[]),
]
_yedek = copy.deepcopy(_env)
eq(kimlik_envanteri(_env), {
    'eski-bot': ['statik-anahtar', 'koda-gomulu-anahtar'],
    'gecis-yarim': ['koda-gomulu-anahtar'],
    'yeni-servis': ['rol-yok'],
    'yonetim-paneli': ['genis-rol'],
    'anahtarli-ama-temiz-kod': ['statik-anahtar'],
}, 'her servis kendi bulgularıyla; temiz servis listede yok')
eq(_env, _yedek, 'girdi değişmemeli')
eq(kimlik_envanteri([]), {}, 'boş envanter')
eq(kimlik_envanteri([_s('a', kimlik='anahtar', roller=['Reader'])]), {'a': ['statik-anahtar', 'genis-rol']},
   'anahtarlı serviste de geniş rol raporlanır; rol-yok yalnız yönetilen kimlikte')

raises(ValueError, kimlik_envanteri, tuple(_env), msg='liste olmayan envanter ValueError')
for _bozuk in (
    ['servis'],
    [{'kimlik': 'yonetilen', 'anahtar_kodda': False, 'roller': []}],
    [_s('')],
    [_s('  ')],
    [dict(_s('a'), ad=5)],
    [_s('a', kimlik='sertifika')],
    [dict(_s('a'), anahtar_kodda=0)],
    [dict(_s('a'), roller=_U)],
    [_s('a', roller=[_U, None])],
    [_s('a'), _s('a')],
):
    raises(ValueError, kimlik_envanteri, _bozuk, msg=f'bozuk servis ValueError: {_bozuk!r}')
```

```hint
Bulguları dört bağımsız `if` ile topla; `elif` kullanırsan statik anahtarlı ve aynı zamanda anahtarı kodda olan servisin ikinci bulgusunu kaybedersin.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Geçiş (25 sn).** "Statik API anahtarı kim taşıyorsa onundur. Yönetilen kimlik ise kısa ömürlü token ve role bağlı izin verir; Azure ve Vertex aynı kalıbı kullanıyor."
2. **İmza yetmez (30 sn).** "İmza token'ı kimin ürettiğini söyler. Bu istek için geçerli olup olmadığını aud, sub, exp ve nbf söyler. Başka hizmete verilmiş bir token aud kontrolüyle düşer."
3. **Sınırlar (25 sn).** "RFC 7519'a göre şimdiki zaman exp'ten önce olmalı. Testte exp eşit now olduğunda reddi ve liste biçimli aud'u ayrıca sınadım."
4. **Envanter (30 sn).** "Servisleri taradık: yönetilen kimliğe geçip eski anahtarı kodda bırakan servisi ve dar rol yerine Owner taşıyan paneli ayrı ayrı yakaladık."
5. **Sınır (10 sn).** "Token çözülmüyor, imza doğrulanmıyor; verified bayrağı platformun kararını temsil ediyor."
:::

::: anlat Sınır ve kaynak
Bu ders iddia denetimini sentetik sözlüklerle modeller. Gerçek bir doğrulayıcı imza algoritmasını, anahtar kimliğini (`kid`), saat kaymasını (*clock skew*) ve token'ı veren tarafı (`iss`) da denetler; bunlar burada yoktur. `scope` alanı RFC 7519'da tanımlı değildir, platforma özgü yetkiyi temsil eden sentetik bir alandır. `Cognitive Services OpenAI User` dışındaki her rolün "geniş" sayılması bu dersin sözleşmesidir; gerçek bir rol tasarımında hangi rolün yeterli olduğu iş akışına göre belirlenir.

- Birincil kaynaklar: [IETF RFC 7519 — JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519) (bölüm 4.1.2–4.1.5: `sub`, `aud`, `exp`, `nbf`); [Microsoft Learn — Azure OpenAI ile Microsoft Entra ID kimlik doğrulaması](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/managed-identity) (API anahtarı saklamadan çağrı, `Cognitive Services OpenAI User` rolü); [Google Cloud — Vertex AI access control with IAM](https://cloud.google.com/vertex-ai/docs/general/access-control). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir ekip yönetilen kimliğe geçti ama eski anahtarı "acil durumda lazım olur" diye kaynakta bıraktı. Anahtarı silmek yerine döndürmek (rotate) neden yetmez? Anahtarın hâlâ kullanıldığını hangi kayıtlardan anlarsın?
:::

::: ozet
- Statik API anahtarı taşıyanındır; yönetilen kimlik kısa ömürlü token ve role bağlı izin verir.
- İmza token'ın kaynağını kanıtlar; isteğe uygunluğunu `aud`, `sub`, `exp`, `nbf` ve kapsam belirler.
- RFC 7519'a göre `aud` liste olabilir ve şimdiki zaman `exp`'ten önce olmalıdır.
- Kimlik envanteri yönetilen kimliğe geçişin yarım kaldığı yerleri (kodda kalan anahtar, geniş rol) gösterir.
:::
