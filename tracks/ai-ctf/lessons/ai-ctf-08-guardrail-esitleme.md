---
id: ai-ctf-08
title: "Kodlama Sırası · Denetimden Sonra Çözümleme Hatası"
summary: Güvenlik denetimini ham metin üzerinde yapıp base64 çözümlemesini denetimden sonra çalıştıran hedefte bayrağı çıkar; ardından kodlama sırası açığını kapatan politikayı kur.
esleme: ai-saldiri-38, ai-saldiri-45, ai-savunma-06, ai-savunma-10
timeout: 30
---

::: anlat 1. Hedef kartı · önce süz, sonra çöz (`check-before-decode`) hatası
Girdi muhafızlarında (`input guardrail`) en yaygın mimari hatalardan biri, güvenlik denetimini **ham girdi** üzerinde çalıştırıp ardından arka uçta `base64`, URL kodlaması veya Unicode normalizasyonu çözmektir (`ai-saldiri-38`, `ai-savunma-10`). Denetleyici ile işleyici aynı verinin farklı aşamalarını gördüğünde saldırı yükü muhafızın önünden kodlanmış halde geçer ve işleyicide açılır.

Hedef 8 bir metin sınıflandırma ucu (`classify`) sunar: ham `text` içinde yasaklı tetikleyiciyi arar, hemen ardından `encoding` seçeneğine göre metni çözüp sınıflandırıcıya verir.

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → JSON nesnesi dizgesi (`<= 4000` karakter) |
| Keşif komutları | `{"op": "help"}` ve `{"op": "ping"}` |
| Sorgu bütçesi | Her hedefte en çok `6` çağrı |
| İşlem alanları | `classify`: `text` (`str`) ve `encoding` (`'plain'` veya `'base64'`) |
| Kabul ölçütü | Kodlama sırası hatasından yararlanarak elde edilen tam `PAFTA{32 hex}` bayrağı |
:::

::: gorev 1 · Denetim sırası farkıyla bayrağı çıkar
`bayrak_al_8(sor)` işlevini yaz. `help` ile `classify` parametrelerini incele; ham metinde engellenen `'CANARY'` tetikleyicisini hedefin desteklediği alternatif kodlamayla göndererek tam `PAFTA{...}` bayrağını döndür.

KUSURLU başlangıç `'CANARY'` dizgesini düz metin olarak gönderdiği için hedefin ön filtresine takılıp `'RED'` alıyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_8(sor):
    print(sor(json.dumps({'op': 'help'})))
    return sor(json.dumps({'op': 'classify', 'text': 'CANARY', 'encoding': 'plain'}))

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(8)
    print(bayrak_al_8(_demo))
```

```solution
import base64
import json

def bayrak_al_8(sor):
    sor(json.dumps({'op': 'help'}))
    kodlu = base64.b64encode(b'CANARY').decode('ascii')
    return sor(json.dumps({'op': 'classify', 'text': kodlu, 'encoding': 'base64'}))


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(8)
    print(bayrak_al_8(_demo))
```

```test
need('bayrak_al_8')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(8)
    _cevap = bayrak_al_8(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu')
    ok(_dogrula(_cevap), 'kodlama sırası farkıyla bayrak çıkarılmalı')
    ok(1 <= _say() <= 6, 'sorgu bütçesi 1..6 aralığında kalmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde taze bayrak')
    _seen.add(_cevap)
_sor, _, _ = hedef_kur(8)
eq(_sor(json.dumps({'op': 'classify', 'text': 'CANARY', 'encoding': 'plain'})), 'RED', 'ham CANARY hedefte engellenir')
```

```hint
Hedef önce `'CANARY' in text` kontrolü yapıyor, sonra `encoding == 'base64'` ise `b64decode` çalıştırıyor. `b'CANARY'` dizisini `base64` ile kodlayıp `encoding: 'base64'` ile gönder.
```
:::

::: tahmin Denetleyici ve işleyici neden aynı temsili görmek zorundadır?
Aşağıdaki iki ardışık satırın sırası değiştiğinde güvenlik kararı nasıl tersine döner?

```python
import base64

yuk = base64.b64encode(b'CANARY').decode('ascii')

once_suz_red = 'CANARY' in yuk
cozulmus = base64.b64decode(yuk).decode('ascii')
sonra_suz_red = 'CANARY' in cozulmus

print('kodlu dizge:', yuk)
print('çözmeden önce süzgeç yakaladı mı:', once_suz_red)
print('çözdükten sonra süzgeç yakaladı mı:', sonra_suz_red)
```

???

```cikti
kodlu dizge: Q0FOQVJZ
çözmeden önce süzgeç yakaladı mı: False
çözdükten sonra süzgeç yakaladı mı: True
```
`'Q0FOQVJZ'` dizgesinde `'CANARY'` harfleri görünmez; dolayısıyla çözümlemeden önce çalışan her kelime/sınıflandırıcı filtresi temiz raporu verir. Kural değişmez: ya tüm kodlamalar kapıda çözülüp **son** metin denetlenir ya da ikincil kodlama biçimleri kapıda reddedilir.
:::

::: anlat 2. Yama mimarisi · kanonik metin sözleşmesi ve yaygın yanlışlar
Kodlama sırası hatasını kapatmanın iki tutarlı yolu vardır:
1. Arka uç `base64` taşımaya ihtiyaç duymuyorsa, giriş politikasında yalnız `'plain'` kodlamaya (açıkça `'plain'` veya varsayılan olarak eksik `'encoding'` anahtarına) izin verip metni doğrudan denetlemek.
2. `base64` zorunluysa, giriş kapısında önce tam aynı kuralla çözüp çözülmüş metni denetlemek ve arka uca yalnız çözülmüş `plain` metni iletmek (böylece iki kez çözme `double-decoding` hatası da önlenir).

Bu dersteki giriş kancası (`izin_8(req)`) `req` sözlüğünü değiştirmeden yalnız `True`/`False` döndürdüğü için 1. yaklaşım uygulanır: yalnız `'plain'` kodlamalı (veya `'encoding'` alanı atlanmış varsayılan) isteklere izin verilir ve `text` içinde `'CANARY'` alt dizgesinin geçmemesi zorunlu tutulur.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `req.get('text') != 'CANARY'` ile tam eşleşme aramak | `'merhaba CANARY'` gibi alt dizge içeren yükleri geçirir (ve `encoding: base64` dalını unutur) | `'CANARY' not in text` ile alt dizge yasağı + `encoding` kısıtı |
| `'CANARY' not in text` yazıp `encoding` alanını kontrol etmemek | `'Q0FOQVJZ'` + `'encoding': 'base64'` yükü yine bayrağı sızdırır | `req.get('encoding', 'plain') == 'plain'` şartını eklemek |
| `req.get('encoding') == 'plain'` yazıp varsayılanı reddetmek | `'encoding'` alanı verilmeyen meşru `{'op': 'classify', 'text': 'merhaba'}` isteğini kırar | `req.get('encoding', 'plain') == 'plain'` ile varsayılanı korumak |
:::

::: gorev 2 · Kodlama atlatmasını ve alt dizge sızıntısını kapatan politika
`izin_8(req)` işlevini yaz ve `bool` döndür. Politika sözleşmesi:

| İşlem (`op`) | Geçerlilik koşulu | Karar |
|---|---|---|
| `'help'` veya `'ping'` | Ek koşul yok | `True` |
| `'classify'` | `req.get('encoding', 'plain') == 'plain'`, `'text'` alanı `str`, `len(text) <= 500` ve `'CANARY' not in text` | `True` |
| Diğer her durum | `'encoding': 'base64'`, `'encoding': None`, `'CANARY'` alt dizgesi içeren metin, eksik veya `str` olmayan `'text'`, `>500` uzunluk veya tanımsız `op` | `False` |

KUSURLU başlangıç yalnız `text != 'CANARY'` kontrolü yapıyor; hem `base64` kodlamasını hem `'not CANARY'` gibi alt dizgeleri kaçırıyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_8(req):
    if not isinstance(req, dict):
        return False
    if req.get('op') in ('help', 'ping'):
        return True
    return req.get('op') == 'classify' and req.get('text') != 'CANARY'
```

```solution
def izin_8(req):
    if not isinstance(req, dict):
        return False
    op = req.get('op')
    if op in ('help', 'ping'):
        return True
    metin = req.get('text')
    return (
        op == 'classify'
        and req.get('encoding', 'plain') == 'plain'
        and isinstance(metin, str)
        and len(metin) <= 500
        and 'CANARY' not in metin
    )
```

```test
need('izin_8')
import base64
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'classify', 'text': 'arsiv duyuru metni'},
    {'op': 'classify', 'text': 'arsiv duyuru metni', 'encoding': 'plain'},
    {'op': 'classify', 'text': ''},
    {'op': 'classify', 'text': 'A' * 500, 'encoding': 'plain'},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_8(_r), True, f'meşru sınıflandırma geçmeli: {_r}')
    eq(_r, _once, 'girdi değişmemeli')

_b64 = base64.b64encode(b'CANARY').decode('ascii')
_kotu = [
    {'op': 'classify', 'text': _b64, 'encoding': 'base64'},
    {'op': 'classify', 'text': 'bWVyaGFiYQ==', 'encoding': 'base64'},
    {'op': 'classify', 'text': 'merhaba', 'encoding': None},
    {'op': 'classify', 'text': 'merhaba', 'encoding': ''},
    {'op': 'classify', 'text': 'CANARY', 'encoding': 'plain'},
    {'op': 'classify', 'text': 'baslik CANARY son', 'encoding': 'plain'},
    {'op': 'classify', 'text': 'CANARY'},
    {'op': 'classify', 'text': 'A' * 501},
    {'op': 'classify'},
    {'op': 'classify', 'text': None},
    {'op': 'classify', 'text': 42},
    {'op': 'export'},
    None,
]
for _r in _kotu:
    eq(izin_8(_r), False, f'kodlanmış veya yasaklı girdi reddedilmeli: {_r}')
eq(izin_8({'op': 'export', 'text': 'normal metin'}), False, 'temiz metin taşısa da classify dışı işlem reddedilmeli')

_sor, _dogrula, _ = hedef_kur(8, butce=8, izin=izin_8)
eq(_sor(json.dumps({'op': 'classify', 'text': 'normal metin'})), 'TEMIZ', 'varsayılan plain sınıflandırma korunur')
eq(_sor(json.dumps({'op': 'classify', 'text': 'normal metin', 'encoding': 'plain'})), 'TEMIZ', 'açık plain sınıflandırma korunur')
_engelli = _sor(json.dumps({'op': 'classify', 'text': _b64, 'encoding': 'base64'}))
eq(_engelli, 'RED', 'base64 atlatması engellenmeli')
ok(not _dogrula(_engelli), 'bayrak sızmamalı')
```

```hint
`op == 'classify'` dalında `req.get('encoding', 'plain') == 'plain'`, `isinstance(metin, str)`, `len(metin) <= 500` ve `'CANARY' not in metin` koşullarının beşini birden uygula.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sorun (15 sn).** "Girdi filtresi ham dizgede `'CANARY'` arıyor ama arka uç bu kontrolden sonra `base64` çözüyor."
2. **Kanıt (30 sn).** "`'CANARY'` dizgesini `Q0FOQVJZ` olarak kodlayıp `encoding: 'base64'` ile gönderdim; ön filtreyi geçip arka uçta çözülerek bayrağı verdi."
3. **Tuzak (30 sn).** "`text != 'CANARY'` tam eşleşmesi alt dizgeleri kaçırır; `encoding` alanını kontrol etmemek ise `base64` atlatmasını olduğu gibi açık bırakır."
4. **Yama (25 sn).** "`izin_8` politikasında etkin kodlamayı `'plain'` ile sınırladım, açık `str` ve `<= 500` uzunluk kontrolüyle birlikte `'CANARY' not in text` kuralını zorunlu kıldım."
5. **Kapanış (20 sn).** "Güvenlik denetimi her zaman işleyicinin göreceği son kanonik temsil üzerinde yapılmalıdır."
:::

::: anlat Sınır
Bu hedef tek katmanlı `base64` çözümleme sırasını modeller. Gerçek LLM sistemlerinde modelin kendisi eğitim verisinden dolayı `base64`, `hex`, `ROT13`, Mors veya düşük kaynaklı dilleri harici bir `b64decode` kodu olmadan da kendi ağırlıkları içinde çözebilir (`ai-saldiri-45`). Bu nedenle güçlü LLM sistemlerinde yalnız girdi `guardrail` katmanına güvenilmez; model çıktısının tetiklediği eylem ve araç sınırları da ayrıca doğrulanır.

- Birincil kaynaklar: [MITRE CWE-180 — Incorrect Behavior Order: Validate Before Canonicalize](https://cwe.mitre.org/data/definitions/180.html): bu dersteki "önce denetle, sonra çöz" hatasının genel adıdır; doğru sıra kanonikleştirip sonra denetlemektir. [Wei, Haghtalab ve Steinhardt — Jailbroken: How Does LLM Safety Training Fail? (arXiv:2307.02483, Temmuz 2023)](https://arxiv.org/abs/2307.02483). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Uygulamanız meşru olarak `base64` kodlu ekler kabul etmek zorundaysa ve kapıda veriyi çözüp denetledikten sonra arka uca **yine** orijinal `base64` dizgesini gönderirseniz, Python'un `base64.b64decode(..., validate=False)` davranışı yüzünden hangi ayrıştırıcı farkı (`parser differential`) doğabilir?
:::

::: ozet
- Denetimin ham veri üzerinde, çözümlemenin ise denetimden sonra yapılması klasik bir `check-before-decode` zafiyetidir.
- Gereksiz alternatif kodlamalar giriş kapısında kapatılır; gerekli olanlar ise tek bir kanonik çözücüden geçirildikten sonra denetlenir.
- Varsayılan parametre semantiği (`get('encoding', 'plain')`) meşru istemcileri bozmadan korunmalıdır.
:::
