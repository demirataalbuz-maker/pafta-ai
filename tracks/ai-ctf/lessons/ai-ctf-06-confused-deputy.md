---
id: ai-ctf-06
title: "Confused Deputy · Araç Çağrısında Yol Sınırı"
summary: Dosya okuma aracını çağıran adına sınırlandırmayan hedefte özel dizindeki kanaryayı oku; ardından yalnız kanonik kamu yoluna izin veren politikayı kur.
esleme: ai-saldiri-18, ai-saldiri-19, ai-savunma-11, ai-savunma-12
timeout: 30
---

::: anlat 1. Hedef kartı · ayrıcalıklı vekil (`confused deputy`) ve yol normalizasyonu
Bir ajan veya arka uç servisi, kullanıcının doğrudan erişemeyeceği bir dosya sistemine kendi yüksek yetkisiyle eriştiğinde **vekil (`deputy`)** konumuna geçer. Uygulama, modelin veya kullanıcının ürettiği `path` argümanını çağıranın yetki kapsamına (`public/`) kilitlemeden doğrudan dosya okuma aracına iletirse `confused deputy` zafiyeti doğar (`ai-saldiri-18`, `ai-savunma-11`).

Bu yerel benzetimde arşiv servisi kamuya açık belgeleri `public/` altında (örneğin `public/readme.txt`), iç doğrulama kanaryasını ise kardeş `private/canary.txt` yolunda tutar. Gerçek diske erişilmez; yol çözümlemesi bellek içi sözlükte `posixpath.normpath` ile modellenir.

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → JSON nesnesi dizgesi (`<= 4000` karakter) |
| Keşif komutları | `{"op": "help"}` ve `{"op": "ping"}` |
| Sorgu bütçesi | Her hedefte en çok `6` çağrı |
| Araç şeması | `read` işlemi `path` (`str`) alanını alır |
| Kabul ölçütü | İç kanarya yolundan okunan tam `PAFTA{32 hex}` bayrağı |
:::

::: gorev 1 · Dosya okuma aracından iç kanaryayı çıkar
`bayrak_al_6(sor)` işlevini yaz. Önce `help` ile okuma aracının beklediği alan adını doğrula, ardından `private/canary.txt` hedefine ulaşan bir okuma isteğiyle tam bayrağı (`PAFTA{...}`) döndür.

KUSURLU başlangıç yalnız kamuya açık `public/readme.txt` dosyasını okuyup içeriğini döndürüyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_6(sor):
    print(sor(json.dumps({'op': 'help'})))
    return sor(json.dumps({'op': 'read', 'path': 'public/readme.txt'}))

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(6)
    print(bayrak_al_6(_demo))
```

```solution
import json

def bayrak_al_6(sor):
    sor(json.dumps({'op': 'help'}))
    return sor(json.dumps({'op': 'read', 'path': 'public/../private/canary.txt'}))


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(6)
    print(bayrak_al_6(_demo))
```

```test
need('bayrak_al_6')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(6)
    _cevap = bayrak_al_6(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu')
    ok(_dogrula(_cevap), 'iç kanarya okunmalı')
    ok(1 <= _say() <= 6, 'sorgu bütçesi 1..6 aralığında kalmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde yeni kanarya')
    _seen.add(_cevap)
_sor, _, _ = hedef_kur(6)
eq(_sor(json.dumps({'op': 'read', 'path': 'public/readme.txt'})), 'Arsiv acik.', 'kamu dosyası meşru metin verir')
```

```hint
`read` işleminde `path` alanına `'private/canary.txt'` veya üst dizin geçişli `'public/../private/canary.txt'` verdiğinde hedefin yetki kontrolü yapmadığını görebilirsin.
```
:::

::: tahmin Ham dizgede `startswith('public/')` neden `normpath` karşısında çöker?
Birçok geliştirici `confused deputy` açığını kapatmak için "yol `'public/'` ile başlıyorsa izin ver" kuralı yazar, sonra yolu işletim sistemine veya `posixpath.normpath` işlevine teslim eder. Üst dizin (`..`) bileşeni bu sırayı nasıl kırar?

```python
import posixpath

aday = 'public/readme.txt/../../private/canary.txt'
on_ek_gecti = aday.startswith('public/readme.txt')
cozulen_yol = posixpath.normpath(aday)
print('ön ek kontrolü:', on_ek_gecti)
print('çözülen gerçek yol:', cozulen_yol)
```

???

```cikti
ön ek kontrolü: True
çözülen gerçek yol: private/canary.txt
```
Ham dizge `'public/readme.txt'` ile başladığı halde `..` bileşeni yüzünden `normpath` sonrasında bambaşka bir dizine (`private/canary.txt`) düşer. Politika denetimi her zaman **kanonikleştirme (`canonicalization`) tamamlandıktan sonra** ve ters eğik çizgi (`\`) gibi alternatif ayırıcılar elendikten sonra yapılmalıdır.
:::

::: anlat 2. Yama mimarisi · kanonik yol doğrulaması ve yaygın yanlışlar
Hedef 6'da iki ayrı hata birleşebilir:
1. Arka uç `posixpath.normpath(path)` çalıştırır ama çözülen yolun `public/` altında kalıp kalmadığını hiç denetlemez (`'private/canary.txt'` doğrudan geçer).
2. Ön tarafa konulan saf bir `path.startswith('public/')` filtresi ise normalizasyondan **önce** çalıştığı için `'public/../private/canary.txt'` ile aşılır.

Bu arşiv uygulamasının meşru okuma kapsamı tek bir kamu belgesidir (`public/readme.txt`). Güvenli `izin_6(req)` kapısı:
- `path` alanının `str` olduğunu, ters eğik çizgi (`\`) veya kök `/` ile başlamadığını denetler;
- `posixpath.normpath(path) == 'public/readme.txt'` koşuluyla **kanonik sonucu** doğrular (dolayısıyla hem `'private/canary.txt'` hem `'public/../private/canary.txt'` kesin olarak reddedilir).

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `path.startswith('public/')` | `'public/../private/canary.txt'` ön eki sağlar ama özel dizini okur | `posixpath.normpath(path)` sonucunu doğrulamak |
| `'..' not in path` ile yalnız üst dizini yasaklamak | Doğrudan `'private/canary.txt'` verildiğinde `..` olmadığı için geçer | Pozitif kanonik hedef eşlemesi (`== 'public/readme.txt'`) |
| Ters eğik çizgiyi (`\`) yok saymak | Windows/karma ortamlarda `'public\\..\\private'` farklı ayrıştırılabilir | `'\\' not in path` ve `not path.startswith('/')` kontrolü |
:::

::: gorev 2 · Kanonik kamu yolunu zorunlu kılan araç politikası
`izin_6(req)` işlevini yaz ve `bool` döndür. Politika sözleşmesi:

| İşlem (`op`) | Geçerlilik koşulu | Karar |
|---|---|---|
| `'help'` veya `'ping'` | Ek koşul yok | `True` |
| `'read'` | `path` alanı boş olmayan `str` olmalı, `'/'` ile başlamamalı, `'\\'` içermemeli ve `posixpath.normpath(path)` sonucu tam `'public/readme.txt'` olmalı | `True` |
| Diğer her durum | `'private/canary.txt'`, `'public/../private/canary.txt'`, mutlak yol `'/public/readme.txt'`, `'\\'` içeren yol, `str` dışı `path` veya tanımsız `op` | `False` |

KUSURLU başlangıç ham dizgede `startswith('public/')` kontrolü yapıyor; üst dizin geçişi (`..`) ile kanarya sızmaya devam ediyor!

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_6(req):
    if not isinstance(req, dict):
        return False
    if req.get('op') in ('help', 'ping'):
        return True
    yol = req.get('path')
    return req.get('op') == 'read' and isinstance(yol, str) and yol.startswith('public/')
```

```solution
import posixpath

def izin_6(req):
    if not isinstance(req, dict):
        return False
    op = req.get('op')
    if op in ('help', 'ping'):
        return True
    yol = req.get('path')
    if op != 'read' or not isinstance(yol, str) or not yol:
        return False
    if yol.startswith('/') or '\\' in yol:
        return False
    return posixpath.normpath(yol) == 'public/readme.txt'
```

```test
need('izin_6')
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'read', 'path': 'public/readme.txt'},
    {'op': 'read', 'path': 'public/./readme.txt'},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_6(_r), True, f'meşru okuma geçmeli: {_r}')
    eq(_r, _once, 'istek sözlüğü değişmemeli')

_kotu = [
    {'op': 'read', 'path': 'private/canary.txt'},
    {'op': 'read', 'path': 'public/../private/canary.txt'},
    {'op': 'read', 'path': 'public/readme.txt/../private/canary.txt'},
    {'op': 'read', 'path': 'public/readme.txt/../../private/canary.txt'},
    {'op': 'read', 'path': '/public/readme.txt'},
    {'op': 'read', 'path': 'public\\readme.txt'},
    {'op': 'read', 'path': 'public/other.txt'},
    {'op': 'read', 'path': ''},
    {'op': 'read'},
    {'op': 'read', 'path': None},
    {'op': 'read', 'path': ['public/readme.txt']},
    {'op': 'write', 'path': 'public/readme.txt'},
    None,
]
for _r in _kotu:
    eq(izin_6(_r), False, f'yetkisiz veya kanonik dışı yol reddedilmeli: {_r}')
eq(izin_6({'op': 'read', 'path': 'x\\y/../public/readme.txt'}), False, 'ters eğik çizgili yol reddedilmeli: POSIX normpath onu public/readme.txt yapar, Windows ise x\\\\public/readme.txt okur (ayrıştırıcı farkı)')

_sor, _dogrula, _ = hedef_kur(6, butce=8, izin=izin_6)
eq(_sor(json.dumps({'op': 'read', 'path': 'public/readme.txt'})), 'Arsiv acik.', 'meşru kamu dosyası okunur')
for _saldiri in ('private/canary.txt', 'public/../private/canary.txt', 'public/readme.txt/../private/canary.txt'):
    _yanit = _sor(json.dumps({'op': 'read', 'path': _saldiri}))
    eq(_yanit, 'RED', f'yol geçişi engellenmeli: {_saldiri}')
    ok(not _dogrula(_yanit), 'bayrak sızmamalı')
```

```hint
Önce `yol` değerinin `str` olduğunu ve `'/'` ile başlamayıp `'\\'` taşımadığını kontrol et; ardından `posixpath.normpath(yol) == 'public/readme.txt'` ile çözülmüş yolu doğrula.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sorun (15 sn).** "Dosya okuma aracı kendi ayrıcalığıyla çalışıyor ama çağıranın hangi dizine yetkili olduğunu denetlemiyor (`confused deputy`)."
2. **Kanıt (30 sn).** "`read` aracına özel dizini hedefleyen yolu vererek tek sorguda `private/canary.txt` içindeki kanaryayı okudum."
3. **Tuzak (30 sn).** "Ham dizgede `startswith('public/readme.txt')` kontrolü yapmak, `'public/readme.txt/../private/canary.txt'` yükünde `True` dönüp `normpath` sonrasında özel dosyayı açar."
4. **Yama (25 sn).** "Önce ayırıcıları kısıtladım, ardından `posixpath.normpath` sonucunun tam `'public/readme.txt'` olmasını zorunlu kıldım."
5. **Kapanış (20 sn).** "Araç güvenliğinde kural her zaman aynıdır: önce kanonikleştir, sonra çağıranın yetkisiyle karşılaştır."
:::

::: anlat Sınır
Bu alıştırma bellek içi dizge normalizasyonunu (`posixpath.normpath`) kapsar. Gerçek işletim sistemi dosya sistemlerinde `normpath` tek başına sembolik bağları (`symlink`) ve yarış durumlarını (`TOCTOU`) çözmez; gerçek dosya sisteminde `Path.resolve()` ile kök dizin sınırı kontrolü ve işletim sistemi düzeyinde `openat` / `O_NOFOLLOW` ya da kapsayıcı (`namespace`) yalıtımı gerekir (`ai-savunma-13`).

- Birincil kaynaklar: [Norm Hardy — The Confused Deputy (or why capabilities might have been invented), ACM SIGOPS Operating Systems Review 22(4), Ekim 1988](https://doi.org/10.1145/54289.871709): kavramın kaynağı; kendi yazma yetkisiyle çalışan bir derleyicinin, kullanıcının verdiği dosya adıyla faturalama dosyasının üzerine yazdırılmasını anlatır. [OWASP GenAI — LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/): araç eylemlerinin çağıranın yetki kapsamında yürütülmesini (`Execute extensions in user's context`) önerir. Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
`posixpath.normpath('public/sembolik_bag/dosya.txt')` çağrısı diskteki `sembolik_bag` dizininin aslında `/etc` dizinine işaret ettiğini neden bilemez? Gerçek dosya sisteminde bu farkı hangi çağrı kapatır?
:::

::: ozet
- Ayrıcalıklı bir aracın kullanıcının veya modelin seçtiği ham yolu doğrudan açması `confused deputy` zafiyetidir.
- Ham dizge ön eki (`startswith`) ile sonradan yapılan yol normalizasyonu (`normpath`) arasındaki fark üst dizin geçişiyle (`..`) istismar edilir.
- Politika kararı kanonik yol üzerinde ve pozitif `allowlist` ile verilmelidir.
:::
