---
id: ai-ctf-10
title: "Bitirme · Keşfet, Kanıtla ve Yamala"
summary: Çok uçlu hedefte katalogdan bakım kanıtına ve yürütmeye uzanan üç adımlı zinciri bütçe içinde tamamla; ardından yalnız kamuya açık incelemeye izin veren sıkı politikayı kur.
esleme: ai-saldiri-36, ai-saldiri-17, ai-savunma-29, ai-savunma-30
timeout: 30
---

::: anlat 1. Hedef kartı · uçtan uca keşif, istismar kanıtı ve regresyonsuz yama
Bitirme hedefi, önceki dokuz derste ayrı ayrı gördüğün becerileri tek bir yerel servis üzerinde birleştirir:
1. **Bütçeli keşif:** En çok `6` sorguda servisin işlem listesini (`help`), öğe kataloğunu (`catalog`) ve öğe ayrıntılarını (`inspect`) haritalandırmak;
2. **Çok adımlı kanıt:** İç bakım (`maintenance`) öğesinden sızan yürütme kanıtını (`proof`) alıp `execute` işlemiyle taze `PAFTA{32 hex}` bayrağına ulaşmak;
3. **Sıkı yama ve regresyon kontrolü:** Bakım incelemesini ve yürütme ucunu kapatırken kamuya açık katalog ve `public` inceleme hizmetini bozmadan korumak (`ai-savunma-29`, `ai-savunma-30`).

Bu hedef **belirlenimci yerel JSON benzetimidir; ağ, dosya veya canlı model kullanılmaz.**

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → JSON nesnesi dizgesi (`<= 4000` karakter) |
| Sorgu bütçesi | Her hedefte toplam en çok `6` çağrı |
| Dinamik durum | Hem `PAFTA{...}` bayrağı hem iç yürütme `proof` değeri her hedefte yeniden üretilir |
| Kabul ölçütü | Üç adımlı keşif-yürütme zincirinden dönen tam `PAFTA{32 hex}` bayrağı |
:::

::: gorev 1 · Katalogdan yürütmeye uzanan zinciri çöz
`bayrak_al_10(sor)` işlevini yaz. Bütçeyi aşmadan hedefin işlemlerini ve katalog öğelerini keşfet, iç bakım öğesinin döndürdüğü JSON verisinden kanıtı (`proof`) ve hedef işlemi çıkar, son adımda bayrağı alıp döndür.

KUSURLU başlangıç yalnız `catalog` listesini çekip ham JSON dizgesini döndürüyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_10(sor):
    print(sor(json.dumps({'op': 'help'})))
    katalog = sor(json.dumps({'op': 'catalog'}))
    print(katalog)
    return katalog

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(10)
    print(bayrak_al_10(_demo))
```

```solution
import json

def bayrak_al_10(sor):
    sor(json.dumps({'op': 'help'}))
    ogeler = json.loads(sor(json.dumps({'op': 'catalog'})))
    hedef_oge = [x for x in ogeler if x != 'public'][0]
    ayrinti = json.loads(sor(json.dumps({'op': 'inspect', 'name': hedef_oge})))
    return sor(json.dumps({'op': ayrinti['operation'], 'proof': ayrinti['proof']}))


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(10)
    print(bayrak_al_10(_demo))
```

```test
need('bayrak_al_10')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(10)
    _cevap = bayrak_al_10(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu')
    ok(_dogrula(_cevap), 'bitirme hedefinin tam bayrağı doğrulanmalı')
    ok(2 <= _say() <= 6, 'keşif ve yürütme bütçe içinde tamamlanmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde taze bayrak')
    _seen.add(_cevap)
_sor, _, _ = hedef_kur(10)
eq(_sor(json.dumps({'op': 'inspect', 'name': 'public'})), 'Arsiv acik.', 'public öğesi meşru bilgi döndürür')
eq(_sor(json.dumps({'op': 'execute', 'proof': 'sahte'})), 'RED', 'geçersiz kanıt reddedilir')
```

```hint
`catalog` çağrısı JSON dizisi döndürür (`json.loads` ile oku). `'public'` dışındaki bakım öğesini `{'op': 'inspect', 'name': ...}` ile incelediğinde dönen JSON nesnesinde hem çağrılacak işlem adı hem `proof` değeri yer alır.
```
:::

::: tahmin Kara liste (`name != 'maintenance'`) neden `execute` ve tanımsız adları açık bırakır?
Olay sonrasında geliştirici yalnız "bakım öğesinin incelenmesini yasaklayayım: `req.get('name') != 'maintenance'`" derse diğer uçlara ne olur?

```python
def kara_liste_10(req):
    return req.get('name') != 'maintenance'

def izin_listesi_10(req):
    op = req.get('op')
    if op in ('help', 'ping', 'catalog') and 'proof' not in req and 'name' not in req:
        return True
    return op == 'inspect' and req.get('name') == 'public' and 'proof' not in req

for istek in [
    {'op': 'inspect', 'name': 'public'},
    {'op': 'inspect', 'name': 'admin'},
    {'op': 'execute', 'proof': 'sizmis-kanit'},
]:
    print(istek, '-> kara_liste:', kara_liste_10(istek), '| izin_listesi:', izin_listesi_10(istek))
```

???

```cikti
{'op': 'inspect', 'name': 'public'} -> kara_liste: True | izin_listesi: True
{'op': 'inspect', 'name': 'admin'} -> kara_liste: True | izin_listesi: False
{'op': 'execute', 'proof': 'sizmis-kanit'} -> kara_liste: True | izin_listesi: False
```
`execute` çağrısında `'name'` alanı hiç bulunmadığı için `req.get('name') != 'maintenance'` koşulu `True` döner! Böylece başka bir yoldan sızan kanıtla yürütme ucu açık kalır; üstelik yarın kataloğa `'debug'` veya `'admin'` eklendiğinde kara liste onları da geçirir.
:::

::: anlat 2. Yama mimarisi · işlem bazlı en az ayrıcalık tablosu ve yaygın yanlışlar
Kamuya açık bir arşiv uç noktasında izin verilen davranış kümesi net ve küçüktür (`least privilege`):
- Keşif ve sağlık işlemleri (`'help'`, `'ping'`, `'catalog'`) ek yetki veya hedef parametre taşımadan çalışır (`'proof' not in req`).
- İnceleme işlemi (`'inspect'`) **yalnız** `req.get('name') == 'public'` olduğunda ve `'proof'` alanı taşımadığında çalışır.
- İç yönetim işlemi `'execute'` ise kamuya açık sınırda hiçbir koşulda çağrılamaz.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `req.get('name') != 'maintenance'` | `execute` çağrısını, eksik `name` alanını ve gelecekteki `'debug'` öğelerini geçirir | `op == 'inspect' and req.get('name') == 'public'` pozitif eşlemesi |
| Yalnız `op != 'execute'` yazıp `inspect` ucunu açık bırakmak | `maintenance` öğesindeki iç `proof` jetonu sızmaya devam eder | Hem `maintenance` incelemesini hem `execute` ucunu kapatmak |
| `'proof'` taşıyan keşif isteklerini hoş görmek | Şema kirliliğine ve parametre kaçakçılığına (`parameter smuggling`) zemin hazırlar | `'proof' not in req` ile yetki alanını tamamen reddetmek |
:::

::: gorev 2 · Bakım sızıntısını ve yürütmeyi kapatan bitirme politikası
`izin_10(req)` işlevini yaz ve `bool` döndür. Politika sözleşmesi:

| İşlem (`op`) | Geçerlilik koşulu | Karar |
|---|---|---|
| `'help'`, `'ping'` veya `'catalog'` | `'proof' not in req` | `True` |
| `'inspect'` | `req.get('name') == 'public'` ve `'proof' not in req` | `True` |
| Diğer her durum | `op == 'execute'`, `name == 'maintenance'`, `name == 'admin'`, eksik veya `str` dışı `name`, `'proof'` anahtarı taşıyan herhangi bir istek, tanımsız `op` | `False` |

KUSURLU başlangıç yalnız `name == 'maintenance'` değerini engelliyor; `execute` işlemi ve tanımsız `inspect` hedefleri açık kalıyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_10(req):
    if not isinstance(req, dict):
        return False
    return req.get('name') != 'maintenance'
```

```solution
def izin_10(req):
    if not isinstance(req, dict) or 'proof' in req:
        return False
    op = req.get('op')
    if op in ('help', 'ping', 'catalog'):
        return True
    return op == 'inspect' and req.get('name') == 'public'
```

```test
need('izin_10')
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'catalog'},
    {'op': 'inspect', 'name': 'public'},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_10(_r), True, f'meşru kamu işlemi geçmeli: {_r}')
    eq(_r, _once, 'girdi değişmemeli')

_kotu = [
    {'op': 'inspect', 'name': 'maintenance'},
    {'op': 'inspect', 'name': 'admin'},
    {'op': 'inspect', 'name': ''},
    {'op': 'inspect'},
    {'op': 'inspect', 'name': None},
    {'op': 'inspect', 'name': ['public']},
    {'op': 'inspect', 'name': 'public', 'proof': 'x'},
    {'op': 'catalog', 'proof': 'x'},
    {'op': 'execute', 'proof': 'herhangi'},
    {'op': 'execute'},
    {'op': 'delete'},
    {},
    None,
]
for _r in _kotu:
    eq(izin_10(_r), False, f'bakım/yürütme veya bozuk şema reddedilmeli: {_r}')
eq(izin_10({'op': 'execute', 'name': 'public'}), False, 'name=public taşısa da inspect dışı işlem reddedilmeli')

_sor, _dogrula, _ = hedef_kur(10, butce=10, izin=izin_10)
eq(_sor(json.dumps({'op': 'ping'})), 'PONG', 'ping korunur')
ok('public' in json.loads(_sor(json.dumps({'op': 'catalog'}))), 'catalog korunur')
eq(_sor(json.dumps({'op': 'inspect', 'name': 'public'})), 'Arsiv acik.', 'public inceleme korunur')
eq(_sor(json.dumps({'op': 'inspect', 'name': 'maintenance'})), 'RED', 'maintenance sızıntısı engellenir')
eq(_sor(json.dumps({'op': 'execute', 'proof': 'deneme'})), 'RED', 'execute ucu engellenir')
```

```hint
Önce `isinstance(req, dict)` ve `'proof' not in req` şartını kontrol et; sonra `'help'`, `'ping'`, `'catalog'` için `True`, `'inspect'` için yalnız `req.get('name') == 'public'` döndür.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Keşif (15 sn).** "Altı sorguluk bütçede önce `help` ve `catalog` ile kamuya açık uçların yanında unutulmuş `maintenance` öğesini haritalandırdım."
2. **Zincir (30 sn).** "`inspect` ile bakım öğesini okuyup iç `proof` jetonunu ve hedef işlemi (`execute`) çıkardım; dördüncü sorguda bayrağı doğruladım."
3. **Tuzak (30 sn).** "`name != 'maintenance'` gibi kara liste yamaları hem `execute` ucunu açık bırakır hem de eksik veya yeni öğe adlarını geçirir."
4. **Yama (25 sn).** "`izin_10` ile `'proof'` alanını ve `execute` ucunu tamamen kapattım; `inspect` işlemini yalnız `'public'` öğesine kilitledim."
5. **Kapanış (20 sn).** "Mor takım (`purple team`) döngüsü ancak hem saldırı zinciri kanıtlandığında hem de meşru hizmet regresyonsuz korunduğunda tamamlanır."
:::

::: anlat Sınır
On derslik bu CTF yolu, güven sınırlarının mekaniğini ağ ve olasılıksal gürültü olmadan deterministik hedeflerde sınar. Gerçek LLM ve MCP sistemlerinde keşif her zaman açık bir `catalog` çıktısıyla gelmez; sistem istemi sızıntıları, hata mesajları ve yan kanallar birleşir (`ai-saldiri-01`, `ai-saldiri-36`). Bir sonraki yol olan `ai-olay` serisinde bu sınır mekanizmalarının kamuoyuna yansımış gerçek güvenlik olaylarıyla ve birincil CVE/üretici belgeleriyle nasıl örtüştüğünü inceleyeceksin.

- Birincil kaynaklar: [OWASP GenAI — Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/): bu bitirme hedefindeki zincir iki maddeyi birleştirir: iç bakım öğesinin yürütme kanıtını sızdırması LLM02 (Sensitive Information Disclosure), kamuya açık arayüzün yürütme ucunu çalıştırabilmesi LLM06 (Excessive Agency); [Debenedetti ve diğerleri — AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents (arXiv:2406.13352, Haziran 2024)](https://arxiv.org/abs/2406.13352): çok adımlı ajan saldırılarını ve savunmalarını ölçmek için kurulmuş açık değerlendirme ortamıdır. Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
`izin_10` giriş kapısı `inspect(maintenance)` çağrısını engellediği halde `catalog` yanıtında hâlâ `'maintenance'` adının görünmesi bir savunma kusuru mudur? Envanter görünürlüğü ile erişim kontrolü arasındaki farkı nasıl değerlendirirsin?
:::

::: ozet
- Çok adımlı hedeflerde bütçe yönetimi önce şema keşfi (`help`, `catalog`), sonra hedefli inceleme ve yürütme sırasıyla yapılır.
- İç yönetim nesneleri (`maintenance`, `execute`, `proof`) kamuya açık ajan/API arayüzünden hem okuma hem yürütme düzeyinde ayrılmalıdır.
- Tamamlanmış bir güvenlik yaması saldırı zincirini sıfırlarken meşru `public` akışta sıfır regresyon üretir.
:::
