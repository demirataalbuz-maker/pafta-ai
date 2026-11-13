---
id: ai-ctf-03
title: "Çıktı Temsilleri · Kodlama ve Parçalı Sızıntı"
summary: Düz metin dışa aktarımını maskelerken alternatif serileştirme biçimlerini açık bırakan JSON hedefinde bayrağı çıkar; ardından yalnız izinli biçimi kabul eden giriş politikasını kur.
esleme: ai-saldiri-10, ai-saldiri-24, ai-savunma-08, ai-savunma-10
timeout: 30
---

::: anlat 1. Hedef kartı · çok biçimli dışa aktarım ve temsil kaçakçılığı
Uygulamalar çoğu zaman aynı veriyi birden fazla serileştirme biçiminde (`plain`, `base64`, JSON dizisi/parçaları, CSV) dışa aktarır. Güvenlik kontrolü yalnız varsayılan insan-okunur dal (`plain`) üzerinde uygulanıp makine-okunur dallar unutulduğunda, aynı veri farklı bir temsil üzerinden korumasız çıkar (`ai-saldiri-10`, `ai-saldiri-24`).

Bu dersten itibaren hedefler `sandbox.ai_ctf_extended.hedef_kur` üzerindeki **JSON tabanlı yerel API** sözleşmesini kullanır. Ağ bağlantısı veya gerçek model yoktur; her hedefin kanaryası `PAFTA{32 hex}` biçiminde rastgele üretilir.

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → en çok `4000` karakterlik JSON nesnesi dizgesi (`str`) |
| Keşif komutları | `{"op": "help"}` desteklenen işlemleri, `{"op": "ping"}` sağlık durumunu döndürür |
| Sorgu bütçesi | Her hedefte toplam en çok `6` çağrı (hatalı JSON çağrıları da bütçeden düşer) |
| İstek doğrulama | Geçersiz JSON veya sözlük dışı kök (`[]`, `"x"`) `ValueError` fırlatır |
| Politika kancası | `hedef_kur(3, izin=fn)` verildiğinde `fn(req) is True` değilse hedef `'RED'` döndürür |
:::

::: gorev 1 · Alternatif çıktı temsilinden bayrağı çöz
`bayrak_al_3(sor)` işlevini yaz. JSON sorgu arayüzünde önce `help` ile dışa aktarım seçeneklerini keşfet, maskelenmeyen bir çıktı biçiminden kanaryayı al ve tam `PAFTA{...}` dizgesine dönüştürerek döndür.

KUSURLU başlangıç `help` yanıtını ham JSON dizgesi olarak döndürüyor; ne dışa aktarım yapıyor ne de kod çözümü uyguluyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_3(sor):
     yardim = sor(json.dumps({'op': 'help'}))
     print(yardim)
     return yardim

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(3)
    print(bayrak_al_3(_demo))
```

```solution
import base64
import json

def bayrak_al_3(sor):
    sor(json.dumps({'op': 'help'}))
    kodlu = sor(json.dumps({'op': 'export', 'format': 'base64'}))
    return base64.b64decode(kodlu).decode('utf-8')


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(3)
    print(bayrak_al_3(_demo))
```

```test
need('bayrak_al_3')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(3)
    _cevap = bayrak_al_3(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu')
    ok(_dogrula(_cevap), 'kodlanmış veya parçalı çıktıdan tam bayrak çözülmeli')
    ok(1 <= _say() <= 6, 'sorgu bütçesi 1..6 aralığında kalmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde taze kanarya')
    _seen.add(_cevap)
_sor, _dogrula, _ = hedef_kur(3)
eq(_sor(json.dumps({'op': 'export', 'format': 'plain'})), '[GIZLENDI]', 'plain dalı maskelidir')
```

```hint
`{"op": "help"}` çıktısındaki `formats` listesini incele. `plain` dalı `[GIZLENDI]` döndürür; diğer biçimlerden birini seçip Python'da `base64.b64decode(...).decode()` ya da JSON parça birleştirmesiyle tam `PAFTA{...}` bayrağını elde et.
```
:::

::: tahmin Varsayılan parametreyi unutan politika meşru isteğe ne yapar?
Hedef içeride `fmt = req.get('format', 'plain')` kullanıyor; yani istemci `'format'` alanını hiç göndermezse varsayılan biçim `'plain'` oluyor. Yama politikası yalnız `req.get('format') == 'plain'` yazarsa ne olur?

```python
def hedef_bicimi(req):
    return req.get('format', 'plain')

def eksik_politika(req):
    return req.get('op') == 'export' and req.get('format') == 'plain'

istek_acik = {'op': 'export', 'format': 'plain'}
istek_varsayilan = {'op': 'export'}
print('açık plain -> hedef:', hedef_bicimi(istek_acik), '| politika:', eksik_politika(istek_acik))
print('varsayılan -> hedef:', hedef_bicimi(istek_varsayilan), '| politika:', eksik_politika(istek_varsayilan))
```

???

```cikti
açık plain -> hedef: plain | politika: True
varsayılan -> hedef: plain | politika: False
```
Uygulamanın varsayılan değer kuralı (`req.get('format', 'plain')`) ile güvenlik politikasının kuralı (`req.get('format') == 'plain'`) örtüşmediğinde meşru varsayılan çağrılar kırılır; tersi durumda ise saldırgan parametreyi atlayarak güvensiz varsayılana düşebilir. Güvenlik kapısı, arka uç işleyicisiyle aynı varsayılan semantiğini paylaşmalıdır.
:::

::: anlat 2. Yama mimarisi · serileştirme dallarında allowlist ve yaygın yanlışlar
Hedef 3'te sızıntı yalnız `base64` dalında değildir; `chunks` dalı da bayrağı iki parçalı JSON dizisi (`[flag[:12], flag[12:]]`) halinde döndürür. Bu yüzden yalnız `'base64'` biçimini yasaklayan bir `denylist` yaması, `'chunks'` üzerinden tek sorguda aşılır.

Güvenli giriş politikası (`izin_3(req)`), arka ucun meşru sözleşmesini pozitif olarak tanımlar:
- `help` ve `ping` keşif/sağlık işlemlerine izin verilir.
- `export` işlemine **yalnız** etkin biçim `'plain'` olduğunda (açıkça `'plain'` verildiğinde veya `'format'` alanı hiç gönderilmeyip varsayılana bırakıldığında) izin verilir; `'format': None` veya `'chunks'` gibi her sapma reddedilir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `req.get('format') != 'base64'` ile tek biçimi yasaklamak | `'chunks'` biçimi bayrağı iki parça halinde sızdırmaya devam eder | Etkin biçimde yalnız `'plain'` değerine `allowlist` uygulamak |
| `req.get('format') == 'plain'` yazıp eksik anahtarı reddetmek | `{'op': 'export'}` meşru varsayılan çağrısını gereksiz yere bozar | `req.get('format', 'plain') == 'plain'` ile arka uç varsayılanını eşlemek |
| `req.get('format') or 'plain'` kullanmak | `{'op': 'export', 'format': ''}` veya `{'format': None}` gibi bozuk istekleri `'plain'` sayar | Anahtar yokluğunu (`'format' not in req` / `get('format', 'plain')`) boş değerden ayırmak |
:::

::: gorev 2 · Tüm sızıntı temsillerini kapatan giriş politikası
`izin_3(req)` işlevini yaz ve `bool` döndür. `hedef_kur(3, izin=izin_3)` önüne bağlandığında uygulanacak sözleşme:

| İşlem (`op`) | Koşul | Karar |
|---|---|---|
| `'help'` veya `'ping'` | Ek koşul yok | `True` |
| `'export'` | `'format'` anahtarı hiç yoksa (varsayılan) veya değeri tam `'plain'` ise | `True` |
| Diğer her durum | `'base64'`, `'chunks'`, `None`, `''`, bilinmeyen `op` veya `dict` dışı `req` | `False` |

Girdi sözlüğünü değiştirme (`mutate` etme).

KUSURLU başlangıç yalnız `'base64'` biçimini kara listeye alıyor; `'chunks'` dalından bayrak sızmaya devam ediyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_3(req):
    if not isinstance(req, dict):
        return False
    return req.get('format') != 'base64'
```

```solution
def izin_3(req):
    if not isinstance(req, dict):
        return False
    op = req.get('op')
    if op in ('help', 'ping'):
        return True
    return op == 'export' and req.get('format', 'plain') == 'plain'
```

```test
need('izin_3')
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'export'},
    {'op': 'export', 'format': 'plain'},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_3(_r), True, f'meşru istek geçmeli: {_r}')
    eq(_r, _once, 'istek sözlüğü değişmemeli')

_kotu = [
    {'op': 'export', 'format': 'base64'},
    {'op': 'export', 'format': 'chunks'},
    {'op': 'export', 'format': ''},
    {'op': 'export', 'format': None},
    {'op': 'export', 'format': 'PLAIN'},
    {'op': 'export', 'format': ['plain']},
    {'op': 'delete'},
    {},
    None,
    'help',
    ['export'],
]
for _r in _kotu:
    eq(izin_3(_r), False, f'yetkisiz veya bozuk istek reddedilmeli: {_r}')

_sor, _dogrula, _ = hedef_kur(3, butce=10, izin=izin_3)
eq(_sor(json.dumps({'op': 'ping'})), 'PONG', 'yamalı hedefte ping çalışır')
eq(_sor(json.dumps({'op': 'export'})), '[GIZLENDI]', 'varsayılan plain dışa aktarım korunur')
eq(_sor(json.dumps({'op': 'export', 'format': 'plain'})), '[GIZLENDI]', 'açık plain dışa aktarım korunur')
for _fmt in ('base64', 'chunks'):
    _yanit = _sor(json.dumps({'op': 'export', 'format': _fmt}))
    eq(_yanit, 'RED', f'{_fmt} temsili engellenmeli')
    ok(not _dogrula(_yanit), 'sızıntı olmamalı')
```

```hint
`isinstance(req, dict)` kontrolünden sonra `'help'` ve `'ping'` için `True` döndür; `'export'` içinse `req.get('format', 'plain') == 'plain'` kontrolünü kullan ki hem açık `'plain'` hem anahtarsız varsayılan geçsin, ama `'format': ''` veya `'chunks'` reddedilsin.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sorun (15 sn).** "Dışa aktarım servisi `plain` metni maskeliyor ama aynı veriyi üreten `base64` ve `chunks` dallarında maskeleme yok."
2. **Kanıt (30 sn).** "`help` ile üç biçimi gördüm; `plain` `[GIZLENDI]` döndürürken `base64` dalından kodlanmış kanaryayı alıp tek adımda çözdüm."
3. **Tuzak (30 sn).** "Yalnız `base64` biçimini yasaklamak `chunks` dizisini açık bırakır; `req.get('format') == 'plain'` demek ise parametresiz meşru `{'op': 'export'}` çağrılarını bozar."
4. **Yama (25 sn).** "`izin_3` kapısında arka uçla aynı varsayılan semantiğini (`req.get('format', 'plain') == 'plain'`) kullanarak pozitif `allowlist` kurdum."
5. **Kapanış (20 sn).** "Veri maskeleme tek bir çıktı biçimine bağlanamaz; güvenlik kapısı bütün serileştirme dallarını kapsamak zorundadır."
:::

::: anlat Sınır
Bu hedef sabit üç çıktı dalı (`plain`, `base64`, `chunks`) üzerinden temsil farkını gösterir. Gerçek API ve ajan sistemlerinde aynı sorun GraphQL alt alanlarında, hata geri izlerinde (`stack trace`), CSV/PDF dışa aktarımlarında ve `structured output` JSON şemalarında ortaya çıkar (`ai-saldiri-10`). Kalıcı mimaride gizli alanlar serileştirme katmanına hiç girmemeli, görünüm modeli (`DTO` / `projection`) aşamasında ayrılmalıdır.

- Birincil kaynaklar: [OWASP GenAI — LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/); [Wei, Haghtalab ve Steinhardt — Jailbroken: How Does LLM Safety Training Fail? (arXiv:2307.02483, Temmuz 2023)](https://arxiv.org/abs/2307.02483): güvenlik eğitiminin, modelin yeteneği olan ama eğitimin kapsamadığı bir alana genellenememesini (`mismatched generalization`) başarısızlık nedeni olarak adlandırır. Maskenin yalnız bir temsile bakması bu kalıbın uygulama katmanındaki karşılığıdır. Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir REST servisinde `/kullanici/profil` ucu telefon numarasını maskelerken `/kullanici/indir?bicim=csv` ucu veritabanı satırını doğrudan CSV'ye döküyor. Bu hatayı çıktı süzgeci yerine veri erişim katmanında (`data layer`) nasıl önlersin?
:::

::: ozet
- Aynı verinin farklı serileştirme biçimleri (`base64`, `chunks`) ham metin maskesini boşa çıkarır.
- Bir biçimi kara listeye almak (`!= 'base64'`), diğer alternatif temsilleri açık bırakır.
- Güvenlik politikası arka ucun varsayılan parametre davranışıyla (`get('format', 'plain')`) uyumlu olmalı, `None` ve `''` gibi bozuk değerleri ise reddetmelidir.
:::
