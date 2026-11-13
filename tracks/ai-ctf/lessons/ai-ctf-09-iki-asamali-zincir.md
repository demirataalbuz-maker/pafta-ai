---
id: ai-ctf-09
title: "Çok Adımlı Zincir · Retrieval Üzerinden Araç Yetkisi"
summary: Retrieval adımından sızan iç yetki biletini ikinci adımda ayrıcalıklı araca taşıyarak bayrağı çıkar; ardından veri okuma ile araç yetkisini birbirinden ayır.
esleme: ai-saldiri-17, ai-saldiri-25, ai-savunma-12, ai-savunma-34
timeout: 30
---

::: anlat 1. Hedef kartı · okunan veriden ayrıcalıklı araç biletine geçiş
Ajan sistemlerinde en tehlikeli kırılmalardan biri **çok adımlı zincir (`multi-step tool chain`)** zafiyetidir: tek başına zararsız görünen bir bilgi getirme (`retrieve`) çağrısı iç ortamdan ham bir yetki jetonu (`bearer ticket`) sızdırır; ikinci adımda ajan bu dizgeyi ayrıcalıklı `tool` çağrısına parametre olarak geçirerek yetki yükseltir (`ai-saldiri-17`, `ai-saldiri-25`).

Bu hedefte her hedef kurulduğunda bayraktan bağımsız rastgele bir `ticket` üretilir. İlk adımda bu bileti keşfedip ikinci adımda ayrıcalıklı aracı tetiklemen gerekir.

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → JSON nesnesi dizgesi (`<= 4000` karakter) |
| Keşif komutları | `{"op": "help"}` ve `{"op": "ping"}` |
| Sorgu bütçesi | Her hedefte toplam en çok `6` çağrı (bütün adımlar aynı bütçeyi paylaşır) |
| Zincir yapısı | `retrieve` ve `tool` işlemleri aynı hedefin iç durumunu paylaşır |
| Kabul ölçütü | İki aşamalı zincir sonunda elde edilen tam `PAFTA{32 hex}` bayrağı |
:::

::: gorev 1 · İki adımlı retrieval-araç zinciriyle bayrağı çıkar
`bayrak_al_9(sor)` işlevini yaz. Önce `help` ile iki işlemi ve alanlarını incele; aynı hedef örneği üzerinde önce bileti elde et, ardından bu biletle `tool` işlemini çağırarak tam `PAFTA{...}` bayrağını döndür.

Not: Bilet her `hedef_kur(9)` çağrısında değişir; bir hedeften alınan bilet başka hedefte çalışmaz.

KUSURLU başlangıç geçersiz sabit bir biletle doğrudan `tool` çağırdığı için `'RED'` alıyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_9(sor):
    print(sor(json.dumps({'op': 'help'})))
    return sor(json.dumps({'op': 'tool', 'ticket': 'sabit-bilet'}))

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(9)
    print(bayrak_al_9(_demo))
```

```solution
import json

def bayrak_al_9(sor):
    sor(json.dumps({'op': 'help'}))
    bilet = sor(json.dumps({'op': 'retrieve', 'document': 'TICKET?'}))
    return sor(json.dumps({'op': 'tool', 'ticket': bilet}))


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(9)
    print(bayrak_al_9(_demo))
```

```test
need('bayrak_al_9')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(9)
    _cevap = bayrak_al_9(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu')
    ok(_dogrula(_cevap), 'iki adımlı zincirle taze bayrak alınmalı')
    ok(2 <= _say() <= 6, 'en az retrieve + tool çağrıları bütçe içinde yapılmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde taze bayrak')
    _seen.add(_cevap)
_sor_a, _, _ = hedef_kur(9)
_sor_b, _dogrula_b, _ = hedef_kur(9)
_bilet_a = _sor_a(json.dumps({'op': 'retrieve', 'document': 'TICKET?'}))
eq(_sor_b(json.dumps({'op': 'tool', 'ticket': _bilet_a})), 'RED', 'başka hedefin bileti geçersizdir')
```

```hint
`help` çıktısı `retrieve` işleminin `document: 'TICKET?'` değerine özel yanıt verdiğini gösteriyor. Dönen bilet dizgesini saklayıp aynı `sor` üzerinde `{'op': 'tool', 'ticket': bilet}` çağrısını yap.
```
:::

::: tahmin Tür kontrolsüz `!=` karşılaştırması şema dışı girdiye ne yapar?
Politikada `req.get('document') != 'TICKET?'` yazıp `isinstance(doc, str)` kontrolünü unutursan eksik alanlı veya sayısal alanlı bir istek nasıl değerlendirilir?

```python
def eksik_tip_kontrolu(req):
    return req.get('op') == 'retrieve' and req.get('document') != 'TICKET?'

def tam_sema_kontrolu(req):
    doc = req.get('document')
    return req.get('op') == 'retrieve' and isinstance(doc, str) and 'TICKET?' not in doc

for istek in [{'op': 'retrieve'}, {'op': 'retrieve', 'document': 404}, {'op': 'retrieve', 'document': 'ozet: TICKET?'}]:
    print(istek, '-> eksik:', eksik_tip_kontrolu(istek), '| tam:', tam_sema_kontrolu(istek))
```

???

```cikti
{'op': 'retrieve'} -> eksik: True | tam: False
{'op': 'retrieve', 'document': 404} -> eksik: True | tam: False
{'op': 'retrieve', 'document': 'ozet: TICKET?'} -> eksik: True | tam: False
```
Python'da `None != 'TICKET?'` ve `404 != 'TICKET?'` ifadeleri `True` üretir! Dolayısıyla açık `isinstance(doc, str)` denetimi yapılmadığında şeması bozuk istekler politikadan geçer; ayrıca tam eşitlik (`!=`) alt dizge olarak gömülü `'TICKET?'` sorgularını da gözden kaçırır.
:::

::: anlat 2. Yama mimarisi · zincirin iki halkasını birden kesmek ve yaygın yanlışlar
Çok adımlı saldırılarda derinliğine savunma (`defense in depth`), zincirin tek bir halkasına güvenmez (`ai-savunma-12`, `ai-savunma-34`):
1. **Yetki halkası:** Kullanıcıya açık arşiv asistanının ayrıcalıklı `tool` işlemini çağırma yetkisi olmamalıdır (`op == 'tool'` tamamen kapalı). Ayrıca hiçbir istek dışarıdan `'ticket'` alanı taşımamalıdır (`'ticket' not in req`); yetki bağlamı model çıktısından veya kullanıcı JSON'undan değil, oturum kimliğinden okunur.
2. **Sızıntı halkası:** `retrieve` işlemi yalnız geçerli `str` belge adlarını/metinlerini (`len <= 500`) kabul etmeli ve iç durum sorgulayan `'TICKET?'` işaretçisini reddetmelidir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız `op != 'tool'` yazıp `retrieve` sorgusunu süzmemek | İç yetki bileti (`ticket`) kullanıcıya sızmaya devam eder; başka bir uçta kullanılabilir | Hem `tool` çağrısını kapatmak hem `'TICKET?'` sızıntısını engellemek |
| Yalnız `'TICKET?'` sorgusunu engelleyip `tool` ucunu açık bırakmak | Bilet başka bir günlükten/hatadan sızarsa `tool` ucu doğrudan bayrağı verir | Ayrıcalıklı `tool` işlemini bu sınırda tamamen reddetmek |
| `req.get('document') != 'TICKET?'` yazmak | `None`, `int` veya `'belge TICKET?'` girdilerini `True` sayar | `isinstance(doc, str) and len(doc) <= 500 and 'TICKET?' not in doc` |
:::

::: gorev 2 · Bilet sızıntısını ve ayrıcalıklı aracı kapatan politika
`izin_9(req)` işlevini yaz ve `bool` döndür. Politika sözleşmesi:

| İşlem (`op`) | Geçerlilik koşulu | Karar |
|---|---|---|
| `'help'` veya `'ping'` | `'ticket'` anahtarı taşımamalı | `True` |
| `'retrieve'` | `'ticket' not in req`, `'document'` alanı `str`, `len(document) <= 500` ve `'TICKET?' not in document` | `True` |
| Diğer her durum | `op == 'tool'`, `'ticket'` anahtarı içeren herhangi bir istek, `'TICKET?'` alt dizgesi, eksik veya `str` dışı `'document'`, `>500` uzunluk | `False` |

KUSURLU başlangıç yalnız `op == 'tool'` çağrısını reddediyor; `retrieve` üzerinden iç biletin sızmasına ve `str` dışı `document` alanlarına izin veriyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_9(req):
    if not isinstance(req, dict):
        return False
    return req.get('op') in ('help', 'ping', 'retrieve')
```

```solution
def izin_9(req):
    if not isinstance(req, dict) or 'ticket' in req:
        return False
    op = req.get('op')
    if op in ('help', 'ping'):
        return True
    doc = req.get('document')
    return (
        op == 'retrieve'
        and isinstance(doc, str)
        and len(doc) <= 500
        and 'TICKET?' not in doc
    )
```

```test
need('izin_9')
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'retrieve', 'document': 'arsiv-2026-ozet'},
    {'op': 'retrieve', 'document': ''},
    {'op': 'retrieve', 'document': 'B' * 500},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_9(_r), True, f'meşru retrieve/keşif geçmeli: {_r}')
    eq(_r, _once, 'girdi değişmemeli')

_kotu = [
    {'op': 'retrieve', 'document': 'TICKET?'},
    {'op': 'retrieve', 'document': 'belge icinde TICKET? sorgusu'},
    {'op': 'retrieve'},
    {'op': 'retrieve', 'document': None},
    {'op': 'retrieve', 'document': 123},
    {'op': 'retrieve', 'document': ['arsiv']},
    {'op': 'retrieve', 'document': 'B' * 501},
    {'op': 'retrieve', 'document': 'arsiv', 'ticket': 'abc'},
    {'op': 'help', 'ticket': 'abc'},
    {'op': 'tool', 'ticket': 'herhangi'},
    {'op': 'tool'},
    {},
    None,
]
for _r in _kotu:
    eq(izin_9(_r), False, f'zincir halkası veya bozuk şema reddedilmeli: {_r}')
eq(izin_9({'op': 'tool', 'document': 'normal'}), False, 'temiz belge taşısa da retrieve dışı işlem reddedilmeli')

_sor, _dogrula, _ = hedef_kur(9, butce=8, izin=izin_9)
eq(_sor(json.dumps({'op': 'retrieve', 'document': 'normal'})), 'Arsiv belgesi.', 'meşru belge okunur')
eq(_sor(json.dumps({'op': 'retrieve', 'document': 'TICKET?'})), 'RED', 'bilet sızıntısı engellenir')
eq(_sor(json.dumps({'op': 'tool', 'ticket': 'deneme'})), 'RED', 'tool çağrısı engellenir')
```

```hint
Önce `isinstance(req, dict)` ve `'ticket' not in req` kontrolünü yap; ardından `'retrieve'` dalında `isinstance(doc, str)`, `len(doc) <= 500` ve `'TICKET?' not in doc` koşullarını doğrula.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sorun (15 sn).** "`retrieve` adımı özel bir sorguyla iç yetki biletini metin olarak döndürüyor; `tool` adımı ise bu bileti kimlik kanıtı sanıp ayrıcalıklı işlem yapıyor."
2. **Kanıt (30 sn).** "Aynı bütçe içinde önce `TICKET?` ile anlık bileti okudum, hemen sonraki çağrıda `tool` ucuna vererek bayrağı çıkardım."
3. **Tuzak (30 sn).** "Zincirin yalnız bir halkasını kapatmak kırılgandır; ayrıca `req.get('document') != 'TICKET?'` yazmak `None` ve `int` türlerini `True` olarak geçirir."
4. **Yama (25 sn).** "`izin_9` içinde hem `'ticket'` alanını ve `tool` ucunu kapattım hem de `retrieve` için `str` şeması ve `'TICKET?'` yasağı getirdim."
5. **Kapanış (20 sn).** "Yetki jetonları asla modelin veya kullanıcının okuduğu veri düzleminde taşınmaz; oturum bağlamından bant dışı (`out-of-band`) doğrulanır."
:::

::: anlat Sınır
Bu hedef iki adımlı doğrusal bir zinciri modeller. Gerçek kurumsal ajanlarda zincir üç-dört farklı MCP sunucusuna yayılabilir (örneğin: e-posta oku → özet belleğe yaz → ertesi gün kod deposunda araç çalıştır; bkz. `ai-olay-04` ve `ai-olay-06`). Böyle ortamlarda yalnız tekil istek şemasına bakmak yetmez; oturum boyunca `taint` izleme ve ayrıcalıklı araçlarda insan onayı (`human-in-the-loop`) gerekir.

- Birincil kaynaklar: [Greshake ve diğerleri — Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection (arXiv:2302.12173, Şubat 2023)](https://arxiv.org/abs/2302.12173); [Debenedetti ve diğerleri — AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents (arXiv:2406.13352, Haziran 2024)](https://arxiv.org/abs/2406.13352); [OWASP GenAI — LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Ayrıcalıklı `tool` işlemini tamamen kapatamayacağınız, bazı yetkili kullanıcıların gerçekten çalıştırması gereken bir sistemde, biletin modelin metin çıktısı üzerinden taşınması yerine uygulama katmanında nasıl bağlanmasını (`binding`) tasarlarsın?
:::

::: ozet
- Tek başına düşük riskli görünen bilgi sızıntısı, ikinci adımdaki araç çağrısıyla birleştiğinde tam yetki aşımına dönüşür.
- Yetki kanıtları (`capability` / `session token`) veri getirme kanallarında görünür dizge olarak taşınmamalıdır.
- Savunma hem bilgi sızıntısı halkasını hem yetkisiz araç çağrısı halkasını birlikte kapatmalıdır.
:::
