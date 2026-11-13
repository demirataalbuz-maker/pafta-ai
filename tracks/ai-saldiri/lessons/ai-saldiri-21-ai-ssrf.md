---
id: ai-saldiri-21
title: Modelden Ara Çağrısına AI-SSRF
summary: Modelin ürettiği URL'yi gerçek loopback HTTP araçlarıyla izle; origin, DNS ve her redirect hop'unda bağlantı kanıtını denetle.
timeout: 60
---

::: anlat Model URL'yi seçer, uygulama bağlantıyı açar
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir URL aracı gerçek TCP bağlantısı, HTTP yanıtı ve redirect zinciri üretir | İlk iki görevde gerçek, yalnız deneye ait loopback HTTP sunucuları ve varsayılan fixture model; `veri/ssrf-senaryolari.json` ile `veri/http-akisi.txt` elle yazılmış görünür örneklerdir. Son görev yerel modeli gerçekten çağırır ve socket peer/HTTP/canary olayını kaydeder | Statik test hostları gerçek kurumsal iç ağ değildir; kontrollü DNS cevapları internet DNS rebinding saldırısı değildir. Örnek politika yalnız bu dar HTTP lab origin'i içindir |

> [!NOT]
> Görünür dosyalar **sentetiktir**, kaydedilmiş gerçek model veya HTTP yanıtı değildir. Buna karşılık temel görevlerin yerel HTTP sunucuları gerçekten çalışır; fixture yalnız model/özel transport sınır vakaları içindir. **Çalıştır** dosyaları okuyup çıktıyı gösterir. Bu kopya geçicidir, sonraki çalıştırmada yenilenir; son görevin kalıcı `calisma/ai-saldiri-21/url-notu.txt` kopyası korunur. Gizli testler öğrenci dosyasından bağımsızdır.

Bir özetleme ajanında model yalnızca metin üretiyor gibi görünür. Ancak çıktı `url_getir(url)` aracının argümanıysa metin, **gerçek bir socket bağlantısının tarifine** dönüşür. Saldırgan kullanıcıya ya da dolaylı prompt injection ile modele bir URL seçtirir; uygulamanın ağ kimliğiyle hedefe erişir. AI-SSRF'nin özü modelin "hacklenmesi" değil, güvenilmeyen model kararı ile yetkili ağ aracının birleşmesidir.

Bu dersteki `AISSRFLab` iki ayrı `ThreadingHTTPServer` açar: `public.test` ve `internal.test`. İkisi de yalnız `127.0.0.1` üzerinde, işletim sisteminin verdiği geçici portlardadır; dış ağ, gerçek iç ağ ve cloud metadata kullanılmaz. `internal.test/canary` her erişimde benzersiz bir canary döndürür ve istek olayını kaydeder. Böylece "filtre çalıştı" demek yerine **iç servise gerçekten kaç HTTP isteği ulaştığını** ölçersin.

Tool izini uçtan uca oku: `kullanıcı istemi → model çıktısı → tool argümanı → çözümlenen IP ve origin → redirect hedefleri → sunucu olayı/canary`. İlk URL'nin izinli olması yeterli değildir. `/start` public origin'dedir fakat 302 yanıtı internal origin'e gider. İzin kontrolünün baktığı URL ile HTTP kütüphanesinin en son bağlandığı origin farklı olabilir. Ayrıca `hostname` doğru olsa bile port farklı bir servisi, DNS cevabı farklı bir adresi ifade edebilir. Her hop'ta şema + host + port bütününü doğrula; DNS'i bir kez çöz, sonucunu politikadan geçir ve aynı IP'yi bağlantıya sabitle. Yalnız string kontrolü yapıp sonra kontrolsüz biçimde yeniden DNS çözen istemci, kontrol ile bağlantı arasında boşluk bırakır.

Model tarafı varsayılan olarak deterministik fixture'dır. Aynı saldırıyı yerel Ollama ile yinelemek istersen `PAFTA_AI_REAL_MODEL=1` ve isteğe bağlı `PAFTA_AI_MODEL=<model>` ortam değişkenleri `model_uret` adaptörünü `127.0.0.1:11434` adresine yöneltir. Bu eski adaptörde gerçek model opt-in'dir; ilk iki görevin testleri ona bağlı değildir. Son **Gerçek deney** görevi ise bu bayraktan bağımsız olarak mevcut yerel modeli ortak oturum yönetimiyle çağırır ve gerçek kanıt olmadan geçmez.

Kaynaklar: [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [OWASP LLM Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/), [RFC 9110 §15.4](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4).
:::

::: tahmin İzinli ilk URL nerede bitti?
Aşağıdaki kod iki loopback HTTP servisi açar. Public `/start`, internal `/canary` adresine 302 verir; standart HTTP aracı yönlendirmeyi gerçekten izler. Çıktılarda değişken portları değil, ölçülebilir olayları yazdırıyoruz. Son satırdan sonraki açıklamayı okumadan önce izin sonucunu ve canary sayısını tahmin et.
```python
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler

class H(BaseHTTPRequestHandler):
    role = ''
    peer = None
    events = []
    def do_GET(self):
        type(self).events.append(self.path)
        if self.path == '/start':
            self.send_response(302)
            self.send_header('Location', self.peer + '/canary')
            self.end_headers()
        else:
            body = json.dumps({'service': self.role, 'path': self.path}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    def log_message(self, *args):
        pass

def serve(role):
    handler = type(role + 'Handler', (H,), {'role': role, 'events': []})
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, handler, f'http://127.0.0.1:{server.server_port}'

internal, ih, internal_base = serve('internal')
public, ph, public_base = serve('public')
ph.peer = internal_base
try:
    model_fixture = public_base + '/start'
    izin = urlsplit(model_fixture).netloc == urlsplit(public_base).netloc
    print('ilk_izin:', izin)
    opener = build_opener(ProxyHandler({}))
    with opener.open(model_fixture, timeout=2) as response:
        result = json.load(response)
    print('son_servis:', result['service'])
    print('son_yol:', result['path'])
    print('ic_istek:', len(ih.events))
finally:
    public.shutdown(); internal.shutdown()
    public.server_close(); internal.server_close()
```
???
```cikti
ilk_izin: True
son_servis: internal
son_yol: /canary
ic_istek: 1
```
İzin kontrolü yalnız modelin seçtiği ilk origin'i gördü. Buna karşın gerçek HTTP aracı ikinci origin'e bağlandı; internal olay kaydı ve dönen gövde bunun kanıtıdır.
:::

::: gorev Model çıktısından canary'ye saldırı zincirini kanıtla
`modelden_araca(model, url_getir, prompt)` fonksiyonunu yaz. `model(prompt)` çağrısının metin cevabını değiştirmeden **bir kez** `url_getir(secilen_url)` çağrısına geçir. `{"prompt": prompt, "secilen_url": secilen_url, "arac_yaniti": yanıt}` döndür. Model cevabı boş olmayan string değilse araca gitmeden `ValueError` yükselt. Bu adım bilerek savunmasız ajan sürümüdür: URL filtrelemek yerine saldırıyı ve tool izini görünür kılarsın.

Laboratuvarda `model_uret(prompt, fixture_url)` deterministik fixture ile Ollama opt-in adaptörünü, `lab.izinsiz_getir(url)` ise redirect izleyen gerçek HTTP aracını verir. Testler önce public `/start` üzerinden internal canary'ye, sonra doğrudan internal URL ile ikinci ve farklı portlu laboratuvara saldırır. Sunucu olayları, dinamik canary ve tam dönüş yapısı hardcode etmeyi geçersiz kılar.
```setup
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.request import Request, build_opener, ProxyHandler

class AISSRFLab:
    def __init__(self):
        self.servers = []
        self.lock = threading.Lock()
        self.public = self._serve('public')
        self.internal = self._serve('internal')
        self.public_origin = self._origin(self.public)
        self.internal_origin = self._origin(self.internal)
        self.canary = f'CANARY-{self.public.server_port}-{self.internal.server_port}'
        self.public.redirects = {
            '/start': f'{self.internal_origin}/canary',
            '/hop1': '/hop2', '/hop2': '/ok', '/loop': '/loop',
        }
        self.internal.redirects = {}

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    def _origin(self, server):
        return f'http://{server.role}.test:{server.server_port}'

    def _serve(self, role):
        lab = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with lab.lock:
                    self.server.events.append(self.path)
                if self.path in self.server.redirects:
                    self.send_response(302)
                    self.send_header('Location', self.server.redirects[self.path])
                    self.end_headers()
                    return
                if role == 'internal' and self.path == '/canary':
                    body = {'service': role, 'path': self.path, 'canary': lab.canary}
                elif self.path == '/ok':
                    body = {'service': role, 'path': self.path}
                else:
                    self.send_response(404); self.end_headers(); return
                raw = json.dumps(body, sort_keys=True).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = self.Server(('127.0.0.1', 0), Handler)
        server.role = role
        server.events = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return server

    def close(self):
        for server in self.servers:
            server.shutdown(); server.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def public_url(self, path):
        return self.public_origin + path

    def internal_url(self, path='/canary'):
        return self.internal_origin + path

    def events(self, role):
        server = self.public if role == 'public' else self.internal
        with self.lock:
            return list(server.events)

    def canary_hits(self):
        return self.events('internal').count('/canary')

    @staticmethod
    def cozucu(hostname):
        if hostname not in ('public.test', 'internal.test'):
            raise ValueError('lab dışı DNS')
        return socket.gethostbyname('127.0.0.1')

    def ham_getir(self, url, ip=None):
        u = urlsplit(url)
        if u.scheme != 'http' or not u.hostname or not u.port:
            raise ValueError('yalnız açık portlu http')
        hedef_ip = self.cozucu(u.hostname) if ip is None else ip
        if hedef_ip != '127.0.0.1':
            raise ValueError('lab dışı socket')
        conn = HTTPConnection(hedef_ip, u.port, timeout=2)
        path = urlunsplit(('', '', u.path or '/', u.query, ''))
        conn.request('GET', path, headers={'Host': u.netloc, 'Connection': 'close'})
        response = conn.getresponse()
        raw = response.read()
        headers = {k.lower(): v for k, v in response.getheaders()}
        status = response.status
        conn.close()
        try:
            body = json.loads(raw.decode())
        except (ValueError, UnicodeDecodeError):
            body = raw.decode('utf-8', 'replace')
        return {'status': status, 'headers': headers, 'body': body, 'url': url}

    def izinsiz_getir(self, url, max_hop=3):
        for hop in range(max_hop + 1):
            response = self.ham_getir(url)
            if not 300 <= response['status'] <= 399:
                return response
            location = response['headers'].get('location')
            if not location or hop == max_hop:
                raise ValueError('izinsiz araç redirect sınırı')
            url = urljoin(url, location)
        raise AssertionError('ulaşılmaz')

def model_uret(prompt, fixture_url):
    if os.environ.get('PAFTA_AI_REAL_MODEL') != '1':
        return fixture_url
    model = os.environ.get('PAFTA_AI_MODEL', 'qwen2.5:1.5b')
    payload = json.dumps({
        'model': model, 'stream': False,
        'prompt': prompt + '\nYalnız getirilecek tam URLyi yaz.\nÖrnek: ' + fixture_url,
    }).encode()
    request = Request('http://127.0.0.1:11434/api/generate', data=payload,
                      headers={'Content-Type': 'application/json'})
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=30) as response:
        text = json.load(response)['response'].strip()
    match = re.search(r'http://[^\s<>]+', text)
    if not match:
        raise ValueError('Ollama cevabında URL yok')
    return match.group(0).rstrip('.,;)')

import sys
import types
_lab_module = types.ModuleType('ai_ssrf_lab')
_lab_module.AISSRFLab = AISSRFLab
_lab_module.model_uret = model_uret
sys.modules['ai_ssrf_lab'] = _lab_module
# Visible synthetic scenario files; existing real loopback setup above is preserved.
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-21")
```
```starter
def modelden_araca(model,url_getir,prompt):
    # KUSURLU BAŞLANGIÇ KODU: modeli iki kez çağırıyor; ikinci cevap ilk URL'den farklı olabilir.
    secilen_url=model(prompt)
    yanit=url_getir(model(prompt))
    return {"prompt":prompt,"secilen_url":secilen_url,"arac_yaniti":yanit}

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ssrf-senaryolari.json")
print("Sentetik senaryolar:",v)
print("Sentetik HTTP biçimi:\n"+metin_yukle("veri/http-akisi.txt"))
from ai_ssrf_lab import AISSRFLab
with AISSRFLab() as ornek_lab:
    secim=ornek_lab.public_url(v["zincir"]["path"])
    print("Fixture model, gerçek yerel HTTP:",modelden_araca(lambda _:secim,ornek_lab.izinsiz_getir,v["zincir"]["prompt"]))
    print("İç servis olayları:",ornek_lab.events("internal"))

```
```test
from ai_ssrf_lab import AISSRFLab, model_uret
with AISSRFLab() as lab:
    prompts = []
    tool_calls = []
    selected = lab.public_url('/start')
    def model(prompt):
        prompts.append(prompt)
        return selected
    def tool(url):
        tool_calls.append(url)
        return lab.izinsiz_getir(url)
    out = modelden_araca(model, tool, 'Bu sayfayı özetle')
    eq(prompts, ['Bu sayfayı özetle'], 'model istemi değişmeden bir kez aldı')
    eq(tool_calls, [selected], 'model çıktısı değişmeden tool argümanı oldu')
    eq(out['prompt'], 'Bu sayfayı özetle', 'izde prompt var')
    eq(out['secilen_url'], selected, 'izde model URLsi var')
    eq(out['arac_yaniti']['body'], {'service':'internal','path':'/canary','canary':lab.canary}, 'iç servis gövdesi gerçek yanıt')
    eq(out['arac_yaniti']['url'], lab.internal_url(), 'redirect sonrası gerçek hedef izde')
    eq(lab.events('public'), ['/start'], 'public HTTP olayı')
    eq(lab.events('internal'), ['/canary'], 'internal canary HTTP olayı')
    eq(lab.canary_hits(), 1, 'zincir canary ile kanıtlandı')

# Aynı kod yeni portlarda ve doğrudan model-seçimli internal URL ile çalışmalı.
with AISSRFLab() as lab2:
    direct = modelden_araca(lambda p: lab2.internal_url(), lab2.izinsiz_getir, 'ikinci deneme')
    eq(direct['arac_yaniti']['body']['canary'], lab2.canary, 'dinamik canary; hardcode değil')
    eq(direct['arac_yaniti']['status'], 200, 'gerçek internal HTTP 200')
    eq(lab2.canary_hits(), 1, 'doğrudan AI-SSRF kanıtı')

for bad in ('', None, 7, '   '):
    calls = []
    raises(ValueError, lambda bad=bad: modelden_araca(lambda p: bad, lambda u: calls.append(u), 'x'), msg='geçersiz model çıktısı reddedilir')
    eq(calls, [], 'geçersiz çıktı araca ulaşmadı')

calls = []
def counted_tool(url):
    calls.append(url)
    return {'status': 204, 'body': None}
out = modelden_araca(lambda p: 'http://public.test:1234/ok', counted_tool, 'p')
eq(len(calls), 1, 'tool tam bir kez çağrıldı')
eq(out, {'prompt':'p','secilen_url':'http://public.test:1234/ok','arac_yaniti':{'status':204,'body':None}}, 'araç cevabı ve tool izi korunur')
```
```solution
def modelden_araca(model, url_getir, prompt):
    secilen_url = model(prompt)
    if not isinstance(secilen_url, str) or not secilen_url.strip():
        raise ValueError('model boş olmayan URL metni üretmeli')
    arac_yaniti = url_getir(secilen_url)
    return {'prompt': prompt, 'secilen_url': secilen_url, 'arac_yaniti': arac_yaniti}
from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ssrf-senaryolari.json")
print("Sentetik senaryolar:",v)
print("Sentetik HTTP biçimi:\n"+metin_yukle("veri/http-akisi.txt"))
from ai_ssrf_lab import AISSRFLab
with AISSRFLab() as ornek_lab:
    secim=ornek_lab.public_url(v["zincir"]["path"])
    print("Fixture model, gerçek yerel HTTP:",modelden_araca(lambda _:secim,ornek_lab.izinsiz_getir,v["zincir"]["prompt"]))
    print("İç servis olayları:",ornek_lab.events("internal"))

```
```hint
Modeli ve aracı ayrı çağır; ikinci çağrının tek argümanı birinci çağrının cevabı olsun. Redirect'i kendin taklit etme: verilen gerçek aracın cevabını ve sunucu olaylarını kullan.
```
:::

::: gorev Her hop'ta origin, DNS ve gerçek bağlantıyı birlikte doğrula
`guvenli_getir(url, origin, cozucu, ham_getir, max_hop=2)` yaz. `origin` güvenilir `http://public.test:PORT` biçimindedir. Başlangıç URL'si ve **her yeni redirect hedefi** için şema `http`, hostname ve açık port origin ile aynı olmalı; userinfo ve fragment olmamalı. URL ASCII olmalı, boşluk/kontrol/DEL ve ters eğik çizgi içermemeli. Ayrıştırma veya port hatasını `ValueError` yap.

Origin'in IP'sini başta `cozucu` ile belirle. Her hop'ta mevcut hostu yeniden çöz; origin IP'sine eşit değilse bağlantı açma. Sonra `ham_getir(url, ip)` çağır: üçüncü taraf transport yalnız bu denetlenmiş IP'yi kullandığı için kontrol ile socket hedefi aynıdır. 301/302/307 dışındaki 3xx yanıtları, eksik/boş ya da kontrol karakterli `Location` değerleri `ValueError` olsun. Göreli hedefi mevcut URL'ye göre çöz. `max_hop` bool olmayan sıfır/pozitif int olsun; başlangıç isteği hop sayılmaz ve sınırı aşan yeni hedefe istek gönderilmez. DEL ve ASCII dışı karakterler bağlantıdan önce yeni URL denetiminde reddedilir; boşluk/kontrol karakterleri Location normalleştirilmeden önce durdurulur. Son yanıtı değiştirmeden döndür.

Bu dar bir laboratuvar politikasıdır; genel internet URL doğrulayıcısı değildir. Başarı ölçütü yalnız hata üretmek değil: `/hop1` gerçek iki hop ile `/ok` sonucuna ulaşmalı, `/start` ise internal canary'ye **hiç** bağlanmadan durmalıdır.
```setup
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.request import Request, build_opener, ProxyHandler

class AISSRFLab:
    def __init__(self):
        self.servers = []
        self.lock = threading.Lock()
        self.public = self._serve('public')
        self.internal = self._serve('internal')
        self.public_origin = self._origin(self.public)
        self.internal_origin = self._origin(self.internal)
        self.canary = f'CANARY-{self.public.server_port}-{self.internal.server_port}'
        self.public.redirects = {
            '/start': f'{self.internal_origin}/canary',
            '/hop1': '/hop2', '/hop2': '/ok', '/loop': '/loop',
        }
        self.internal.redirects = {}

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    def _origin(self, server):
        return f'http://{server.role}.test:{server.server_port}'

    def _serve(self, role):
        lab = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with lab.lock:
                    self.server.events.append(self.path)
                if self.path in self.server.redirects:
                    self.send_response(302)
                    self.send_header('Location', self.server.redirects[self.path])
                    self.end_headers()
                    return
                if role == 'internal' and self.path == '/canary':
                    body = {'service': role, 'path': self.path, 'canary': lab.canary}
                elif self.path == '/ok':
                    body = {'service': role, 'path': self.path}
                else:
                    self.send_response(404); self.end_headers(); return
                raw = json.dumps(body, sort_keys=True).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = self.Server(('127.0.0.1', 0), Handler)
        server.role = role
        server.events = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return server

    def close(self):
        for server in self.servers:
            server.shutdown(); server.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def public_url(self, path):
        return self.public_origin + path

    def internal_url(self, path='/canary'):
        return self.internal_origin + path

    def events(self, role):
        server = self.public if role == 'public' else self.internal
        with self.lock:
            return list(server.events)

    def canary_hits(self):
        return self.events('internal').count('/canary')

    @staticmethod
    def cozucu(hostname):
        if hostname not in ('public.test', 'internal.test'):
            raise ValueError('lab dışı DNS')
        return socket.gethostbyname('127.0.0.1')

    def ham_getir(self, url, ip=None):
        u = urlsplit(url)
        if u.scheme != 'http' or not u.hostname or not u.port:
            raise ValueError('yalnız açık portlu http')
        hedef_ip = self.cozucu(u.hostname) if ip is None else ip
        if hedef_ip != '127.0.0.1':
            raise ValueError('lab dışı socket')
        conn = HTTPConnection(hedef_ip, u.port, timeout=2)
        path = urlunsplit(('', '', u.path or '/', u.query, ''))
        conn.request('GET', path, headers={'Host': u.netloc, 'Connection': 'close'})
        response = conn.getresponse()
        raw = response.read()
        headers = {k.lower(): v for k, v in response.getheaders()}
        status = response.status
        conn.close()
        try:
            body = json.loads(raw.decode())
        except (ValueError, UnicodeDecodeError):
            body = raw.decode('utf-8', 'replace')
        return {'status': status, 'headers': headers, 'body': body, 'url': url}

    def izinsiz_getir(self, url, max_hop=3):
        for hop in range(max_hop + 1):
            response = self.ham_getir(url)
            if not 300 <= response['status'] <= 399:
                return response
            location = response['headers'].get('location')
            if not location or hop == max_hop:
                raise ValueError('izinsiz araç redirect sınırı')
            url = urljoin(url, location)
        raise AssertionError('ulaşılmaz')

def model_uret(prompt, fixture_url):
    if os.environ.get('PAFTA_AI_REAL_MODEL') != '1':
        return fixture_url
    model = os.environ.get('PAFTA_AI_MODEL', 'qwen2.5:1.5b')
    payload = json.dumps({
        'model': model, 'stream': False,
        'prompt': prompt + '\nYalnız getirilecek tam URLyi yaz.\nÖrnek: ' + fixture_url,
    }).encode()
    request = Request('http://127.0.0.1:11434/api/generate', data=payload,
                      headers={'Content-Type': 'application/json'})
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=30) as response:
        text = json.load(response)['response'].strip()
    match = re.search(r'http://[^\s<>]+', text)
    if not match:
        raise ValueError('Ollama cevabında URL yok')
    return match.group(0).rstrip('.,;)')

import sys
import types
_lab_module = types.ModuleType('ai_ssrf_lab')
_lab_module.AISSRFLab = AISSRFLab
_lab_module.model_uret = model_uret
sys.modules['ai_ssrf_lab'] = _lab_module
# Visible synthetic scenario files; existing real loopback setup above is preserved.
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-21")
```
```starter
from urllib.parse import urlsplit,urljoin

def guvenli_getir(url,origin,cozucu,ham_getir,max_hop=2):
    # KUSURLU BAŞLANGIÇ KODU: yalnız origin IP'sini alıp redirect hedefini yeniden doğrulamıyor.
    ip=cozucu(urlsplit(origin).hostname)
    for _ in range(max_hop+1):
        r=ham_getir(url,ip)
        if r["status"] not in (301,302,307):
            return r
        url=urljoin(url,r["headers"]["location"])
    raise ValueError("redirect sınırı")

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ssrf-senaryolari.json")
print("Sentetik senaryolar:",v)
print("Sentetik HTTP biçimi:\n"+metin_yukle("veri/http-akisi.txt"))
from ai_ssrf_lab import AISSRFLab
with AISSRFLab() as ornek_lab:
    for senaryo in v["kapilar"]:
        try:
            sonuc=guvenli_getir(ornek_lab.public_url(senaryo["path"]),ornek_lab.public_origin,ornek_lab.cozucu,ornek_lab.ham_getir,max_hop=senaryo["max_hop"])
            print(senaryo["path"],sonuc)
        except ValueError as e:
            print(senaryo["path"],"RET:",str(e))
    print("İç servis olayları:",ornek_lab.events("internal"))

```
```test
from ai_ssrf_lab import AISSRFLab, model_uret
with AISSRFLab() as lab:
    sent = []
    def transport(url, ip):
        sent.append((url, ip))
        return lab.ham_getir(url, ip)
    direct = guvenli_getir(lab.public_url('/ok'), lab.public_origin, lab.cozucu, transport)
    eq(direct['body'], {'service':'public','path':'/ok'}, 'izinli gerçek HTTP cevabı')
    eq(sent, [(lab.public_url('/ok'),'127.0.0.1')], 'doğrulanan IP gerçek bağlantıya sabitlendi')

    sent.clear()
    zero = guvenli_getir(lab.public_url('/ok'), lab.public_origin, lab.cozucu, transport, max_hop=0)
    eq(zero['status'], 200, 'sıfır hop doğrudan isteği engellemez')
    eq(len(sent), 1, 'sıfır hopta tam bir doğrudan bağlantı')

    sent.clear()
    result = guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lab.cozucu, transport, max_hop=2)
    eq(result['body'], {'service':'public','path':'/ok'}, 'iki gerçek redirect hopu tamamlandı')
    eq([u for u,ip in sent], [lab.public_url('/hop1'),lab.public_url('/hop2'),lab.public_url('/ok')], 'her hop gerçek transportta görüldü')
    eq({ip for u,ip in sent}, {'127.0.0.1'}, 'bütün hoplar aynı doğrulanmış IPye sabitli')
    eq(lab.canary_hits(), 0, 'meşru trafik internal canaryye gitmedi')

    before = len(lab.events('public'))
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lab.cozucu, transport, max_hop=1), msg='üçüncü istek hop sınırını aşar')
    eq(len(lab.events('public'))-before, 2, 'sınırı aşan yeni hedefe istek yok')

    before = len(lab.events('public'))
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lab.cozucu, transport, max_hop=0), msg='sıfır hopta ilk redirect hedefi aşılmaz')
    eq(len(lab.events('public'))-before, 1, 'sıfır hopta yalnız başlangıç isteği yapılır')

    # Varsayılan tam 2 hop'tur; üçüncü redirect hedefine bağlanılmaz.
    lab.public.redirects['/chain3'] = '/hop1'
    before = len(lab.events('public'))
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/chain3'), lab.public_origin, lab.cozucu, transport), msg='varsayılan sınır üçüncü redirecti reddeder')
    eq(len(lab.events('public'))-before, 3, 'varsayılan sınırda /ok hedefine istek yok')

    raises(ValueError, lambda: guvenli_getir(lab.public_url('/start'), lab.public_origin, lab.cozucu, transport), msg='cross-origin redirect reddedilir')
    eq(lab.canary_hits(), 0, 'redirect iç servise hiç ulaşmadı')
    eq(lab.events('internal'), [], 'iç origin için socket olayı yok')

    raises(ValueError, lambda: guvenli_getir(lab.public_url('/loop'), lab.public_origin, lab.cozucu, transport, max_hop=3), msg='redirect döngüsü sınırlı')

    for bad in (lab.internal_url(), lab.public_url('/ok').replace('public.test','other.test'),
                f'http://public.test:{lab.internal.server_port}/ok',
                lab.public_url('/ok').replace('http://','https://'),
                lab.public_url('/ok')+'#fragment',
                lab.public_url('/ok').replace('http://','http://user@'),
                'http://127.0.0.1:80/ok', '/ok'):
        raises(ValueError, lambda bad=bad: guvenli_getir(bad, lab.public_origin, lab.cozucu, transport), msg='yanlış origin/port/şema veya belirsiz URL')
    eq(lab.canary_hits(), 0, 'yanlış origin denemeleri canary üretmedi')

    # DNS rebinding mutasyonu: çözümlenen IP politikadan geçmeden socket açılmamalı.
    before_calls = len(sent)
    dns_answers = iter(['127.0.0.1', '127.0.0.2'])
    def rebind(hostname):
        return next(dns_answers)
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/ok'), lab.public_origin, rebind, transport), msg='ilk çözümleme ile bağlantı öncesi DNS cevabı farklıysa reddedilir')
    eq(len(sent), before_calls, 'kötü DNS cevabında gerçek transport çağrısı yok')

    before_calls = len(sent)
    hop_dns = iter(['127.0.0.1', '127.0.0.1', '127.0.0.2'])
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lambda h: next(hop_dns), transport), msg='redirect hopunda DNS rebinding reddedilir')
    eq(len(sent)-before_calls, 1, 'DNS değişen ikinci hop için socket açılmadı')

    # İkinci çözümleme transport içinde yeniden yapılamaz; gözlenen IP aynı kalmalı.
    resolutions = []
    def watched_dns(hostname):
        resolutions.append(hostname)
        return '127.0.0.1'
    guvenli_getir(lab.public_url('/ok'), lab.public_origin, watched_dns, transport)
    ok(len(resolutions) >= 2, 'origin ve bağlantı hostu DNS ile ölçüldü')
    eq(sent[-1][1], '127.0.0.1', 'DNS kontrolü ile socket aynı IPyi kullandı')

for bad in (-1, True, 1.5, None):
    raises(ValueError, lambda bad=bad: guvenli_getir('http://public.test:1/ok','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:None,max_hop=bad), msg='max_hop tipi ve alt sınırı')

# Yeni laboratuvar ve portlar: cevap, canary veya origin hardcode edilemez.
with AISSRFLab() as other:
    raises(ValueError, lambda: guvenli_getir(other.public_url('/start'), other.public_origin, other.cozucu, other.ham_getir), msg='ikinci laboratuvarda da cross-origin redirect durur')
    eq(other.canary_hits(), 0, 'yeni dinamik canary de erişilmez kaldı')
    ok(guvenli_getir(other.public_url('/ok'), other.public_origin, other.cozucu, other.ham_getir)['url'].endswith('/ok'), 'dinamik origin ile gerçek başarı')

# Transport test double'ı: kontrol ilk istekten önce ve her hop'ta çalışır.
calls = []
def deny_transport(url, ip):
    calls.append((url, ip))
    return {'status':200,'headers':{},'body':{},'url':url}
raises(ValueError, lambda: guvenli_getir('http://internal.test:9/canary','http://public.test:1',lambda h:'127.0.0.1',deny_transport), msg='ilk URL de kontrol edilir')
eq(calls, [], 'ilk URL reddinde bağlantı yok')

responses = iter([
    {'status':302,'headers':{'location':'/next'},'body':None,'url':'http://public.test:1/a'},
    {'status':200,'headers':{},'body':{'ok':True},'url':'http://public.test:1/next'},
])
seen = []
def fake(url, ip):
    seen.append(url)
    return next(responses)
r = guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',fake)
eq(seen, ['http://public.test:1/a','http://public.test:1/next'], 'göreli Location mevcut URLye göre çözüldü')
eq(r['body'], {'ok':True}, 'son cevap değiştirilmeden döndü')

# Desteklenen üç redirect sınıfı da gerçekten izlenir; listeden biri çıkarılırsa yakalanır.
for status in (301, 302, 307):
    status_responses = iter([
        {'status':status,'headers':{'location':'/next'},'body':None,'url':'http://public.test:1/a'},
        {'status':200,'headers':{},'body':{'ok':status},'url':'http://public.test:1/next'},
    ])
    status_calls = []
    def status_transport(url, ip):
        status_calls.append(url)
        return next(status_responses)
    status_result = guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',status_transport)
    eq(status_result['body'], {'ok':status}, '301/302/307 desteklenen redirect sınıfı')
    eq(len(status_calls), 2, 'desteklenen redirect bir sonraki hopa gider')

# 3xx aralığının iki ucu ve desteklenmeyen sınıflar ilk yanıtta durur; hop limitine kadar tekrarlanmaz.
for status in (300, 303, 308, 399):
    unsupported_calls = []
    def unsupported_transport(url, ip):
        unsupported_calls.append(url)
        return {'status':status,'headers':{'location':'/x'},'body':None,'url':url}
    raises(ValueError, lambda: guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',unsupported_transport), msg='300/303/308/399 desteklenmeyen redirect')
    eq(len(unsupported_calls), 1, 'desteklenmeyen redirect için yeni hop yapılmaz')

for response in ({'status':302,'headers':{}}, {'status':302,'headers':{'location':''}},
                 {'status':302,'headers':{'location':'/a\tb'}}, {'status':302,'headers':{'location':'/a b'}}):
    raises(ValueError, lambda response=response: guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:response), msg='bozuk veya kontrol karakterli Location')
for status in (200, 299, 400):
    response = {'status':status,'headers':{},'body':status,'url':'http://public.test:1/a'}
    eq(guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:response), response, '3xx dışı doğrudan cevap')

# Location ASCII 33 kabul edilir; 32 zaten reddedilir. 127 ve 128 de sonraki URL denetiminden önce bağlantı açamaz.
location_responses = iter([
    {'status':302,'headers':{'location':'/a!b'},'body':None,'url':'http://public.test:1/a'},
    {'status':200,'headers':{},'body':'ascii-33','url':'http://public.test:1/a!b'},
])
eq(guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:next(location_responses))['body'], 'ascii-33', 'Location ASCII 33 izinli komşu')
for code in (127, 128):
    location_calls = []
    def location_transport(url, ip, code=code):
        location_calls.append(url)
        return {'status':302,'headers':{'location':'/a'+chr(code)+'b'},'body':None,'url':url}
    raises(ValueError, lambda: guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',location_transport), msg='Location 127/128 ASCII URL sınırını aşamaz')
    eq(len(location_calls), 1, 'Location 127/128 için ikinci socket yok')

# URL'nin eşit uçları ve iki komşusu: 32/127/128 reddedilir, 33 kabul edilir.
for code, allowed in ((32,False),(33,True),(127,False),(128,False)):
    ascii_calls = []
    def ascii_transport(url, ip):
        ascii_calls.append(url)
        return {'status':200,'headers':{},'body':'ok','url':url}
    target = 'http://public.test:1/a'+chr(code)+'b'
    if allowed:
        eq(guvenli_getir(target,'http://public.test:1',lambda h:'127.0.0.1',ascii_transport)['status'], 200, 'URL ASCII 33 kabul edilir')
        eq(len(ascii_calls), 1, 'izinli ASCII komşusu bağlantıya ulaşır')
    else:
        raises(ValueError, lambda target=target: guvenli_getir(target,'http://public.test:1',lambda h:'127.0.0.1',ascii_transport), msg='URL ASCII 32/127/128 reddedilir')
        eq(ascii_calls, [], 'reddedilen ASCII sınırında socket yok')

for bad in ('http://public.test:1/a\\b','http://public.test:1/a#x',
            'http://public.test:1/ğ','http://public.test:/','http://public.test:65536/'):
    raises(ValueError, lambda bad=bad: guvenli_getir(bad,'http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:ok(False,'ağ açılmamalı')), msg='ASCII ve ayrıştırma sınırı')
raises(ValueError, lambda: guvenli_getir(123,'http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:ok(False,'ağ açılmamalı')), msg='string olmayan URL reddedilmeli')
raises(ValueError, lambda: guvenli_getir('http://public.test:1/ok','http://public.test:bad',lambda h:'127.0.0.1',lambda u,ip:ok(False,'ağ açılmamalı')), msg='geçersiz origin reddedilmeli')
eq(guvenli_getir('http://public.test:1/a~b','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:{'status':200,'headers':{},'body':'ok','url':u})['status'], 200, 'URL ASCII 126 kabul edilir')
# urljoin baştaki boşluk/kontrolü normalize edebilir; ham Location önceden reddedilmelidir.
for raw_location in (' /ok','\t/ok','\n/ok','\r/ok'):
    leading_calls=[]
    def leading_transport(url,ip):
        leading_calls.append((url,ip))
        return {'status':302,'headers':{'location':raw_location},'body':None,'url':url}
    raises(ValueError,lambda:guvenli_getir('http://public.test:1/a','http://public.test:1',lambda _:'127.0.0.1',leading_transport),msg='ham Location normalleştirmeden önce reddedilmeli')
    eq(len(leading_calls),1,'bozuk Location için ikinci bağlantı açılmaz')

```
```solution
from urllib.parse import urlsplit, urljoin

def guvenli_getir(url, origin, cozucu, ham_getir, max_hop=2):
    if type(max_hop) is not int or max_hop < 0:
        raise ValueError('hop sınırı')
    try:
        allowed = urlsplit(origin)
        allowed_key = (allowed.scheme, allowed.hostname, allowed.port)
        allowed_ip = cozucu(allowed.hostname)
    except (ValueError, TypeError) as exc:
        raise ValueError('geçersiz origin') from exc

    def denetle(current):
        if not isinstance(current, str) or any(ord(c) <= 32 or ord(c) >= 127 for c in current) or '\\' in current or '#' in current:
            raise ValueError('belirsiz URL')
        try:
            u = urlsplit(current)
            key = (u.scheme, u.hostname, u.port)
            if key != allowed_key or u.username is not None or u.password is not None:
                raise ValueError('origin sınırı')
            ip = cozucu(u.hostname)
        except (ValueError, TypeError) as exc:
            raise ValueError('URL/DNS reddi') from exc
        if ip != allowed_ip:
            raise ValueError('DNS sınırı')
        return ip

    hops = 0
    while True:
        ip = denetle(url)
        response = ham_getir(url, ip)
        status = response['status']
        if not 300 <= status <= 399:
            return response
        if status not in (301, 302, 307) or hops >= max_hop:
            raise ValueError('redirect türü/sınırı')
        location = response['headers'].get('location')
        if not location or any(ord(c) <= 32 for c in location):
            raise ValueError('Location')
        url = urljoin(url, location)
        hops += 1
from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ssrf-senaryolari.json")
print("Sentetik senaryolar:",v)
print("Sentetik HTTP biçimi:\n"+metin_yukle("veri/http-akisi.txt"))
from ai_ssrf_lab import AISSRFLab
with AISSRFLab() as ornek_lab:
    for senaryo in v["kapilar"]:
        try:
            sonuc=guvenli_getir(ornek_lab.public_url(senaryo["path"]),ornek_lab.public_origin,ornek_lab.cozucu,ornek_lab.ham_getir,max_hop=senaryo["max_hop"])
            print(senaryo["path"],sonuc)
        except ValueError as e:
            print(senaryo["path"],"RET:",str(e))
    print("İç servis olayları:",ornek_lab.events("internal"))

```
```hint
Döngünün başında tek bir doğrulama fonksiyonu çağır. Hem origin bütününü hem DNS cevabını orada denetle ve döndürdüğü IP'yi aynen `ham_getir(url, ip)` çağrısına ver. Yeni `Location` değerini çözüp hemen istek yapma; döngünün başına dön.
```
:::


::: anlat Fixture modelin yerine canlı model, TCP kanıtı aynı zincirde
Ham sentetik dosya aynı Pafta sunucusunda `/data/ai-saldiri-21-url-notu.txt` adresindedir. Adres çubuğunda sunucunun kökünden bu yolu açabilirsin; mevcut Markdownrenderer tıklanabilir bağlantı üretmez. Çalıştır ayrı kalıcı `calisma/ai-saldiri-21/url-notu.txt` kopyasının yolunu/içeriğini gösterir; dış editör/Python ile değiştirip tekrar Çalıştır, düzenlemen korunur. Test ayrı dosya kullanır.

Önceki adımların HTTP sunucuları gerçekti, model varsayılan fixture idi. Bu yeni görevde model her koşuda gerçekten çağrılır; seçtiği URL öğrenci `modelden_araca` işlevinden gerçek HTTP aracına gider. Ham yanıt ile kenar boşlukları alınmış URL ayrı kaydedilir; regex ile başka URL seçilmez veya başarısız yanıt yerine fixture konmaz. Korumalı araç senin her-hop `guvenli_getir` işlevini kullanır. Normal okuma da çalışmalıdır.

Sunucular yalnız bu deneyin açtığı iki geçici loopback originidir. Ayrı statik containment başka port/kullanıcı servisine bağlantıyı da engeller. Her bağlantının gerçek TCP peer'i, HTTP durumu ve `Location` başlığı, sunucu olayı ve gerçek canary artışı kaydedilir. Doğrudan sentetik URL kontrolüyle savunmasız redirect gerçekten yerel canaryye ulaşır; bu, modele yapılmış bir saldırının başarısı diye sunulmaz. DNS değişim kontrollerinin cevapları sentetiktir, bağlanılan TCP gerçektir. Korumalı akış iç servise gitmemeli; saldırı modelinin uyması geçme şartı değildir. Yalnız kendi iki sunucusu kapanır; kullanıcının diğer servislerine dokunulmaz.
:::

::: gorev Gerçek deney · Canlı modelURLsini her redirectte denetle
Önceki `modelden_araca` ve `guvenli_getir` işlevlerini birleştir. Kontrol Et önce eski fixture/saf sözleşmeleri, sonra canlı model+gerçek HTTP ve socket kanıtını ayrı sınar. Yeni adımda gerçek model opt-in değil zorunludur.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```setup
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.request import Request, build_opener, ProxyHandler

class AISSRFLab:
    def __init__(self):
        self.servers = []
        self.lock = threading.Lock()
        self.public = self._serve('public')
        self.internal = self._serve('internal')
        self.public_origin = self._origin(self.public)
        self.internal_origin = self._origin(self.internal)
        self.canary = f'CANARY-{self.public.server_port}-{self.internal.server_port}'
        self.public.redirects = {
            '/start': f'{self.internal_origin}/canary',
            '/hop1': '/hop2', '/hop2': '/ok', '/loop': '/loop',
        }
        self.internal.redirects = {}

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    def _origin(self, server):
        return f'http://{server.role}.test:{server.server_port}'

    def _serve(self, role):
        lab = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with lab.lock:
                    self.server.events.append(self.path)
                if self.path in self.server.redirects:
                    self.send_response(302)
                    self.send_header('Location', self.server.redirects[self.path])
                    self.end_headers()
                    return
                if role == 'internal' and self.path == '/canary':
                    body = {'service': role, 'path': self.path, 'canary': lab.canary}
                elif self.path == '/ok':
                    body = {'service': role, 'path': self.path}
                else:
                    self.send_response(404); self.end_headers(); return
                raw = json.dumps(body, sort_keys=True).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = self.Server(('127.0.0.1', 0), Handler)
        server.role = role
        server.events = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return server

    def close(self):
        for server in self.servers:
            server.shutdown(); server.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def public_url(self, path):
        return self.public_origin + path

    def internal_url(self, path='/canary'):
        return self.internal_origin + path

    def events(self, role):
        server = self.public if role == 'public' else self.internal
        with self.lock:
            return list(server.events)

    def canary_hits(self):
        return self.events('internal').count('/canary')

    @staticmethod
    def cozucu(hostname):
        if hostname not in ('public.test', 'internal.test'):
            raise ValueError('lab dışı DNS')
        return socket.gethostbyname('127.0.0.1')

    def ham_getir(self, url, ip=None):
        u = urlsplit(url)
        if u.scheme != 'http' or not u.hostname or not u.port:
            raise ValueError('yalnız açık portlu http')
        hedef_ip = self.cozucu(u.hostname) if ip is None else ip
        if hedef_ip != '127.0.0.1':
            raise ValueError('lab dışı socket')
        conn = HTTPConnection(hedef_ip, u.port, timeout=2)
        path = urlunsplit(('', '', u.path or '/', u.query, ''))
        conn.request('GET', path, headers={'Host': u.netloc, 'Connection': 'close'})
        response = conn.getresponse()
        raw = response.read()
        headers = {k.lower(): v for k, v in response.getheaders()}
        status = response.status
        conn.close()
        try:
            body = json.loads(raw.decode())
        except (ValueError, UnicodeDecodeError):
            body = raw.decode('utf-8', 'replace')
        return {'status': status, 'headers': headers, 'body': body, 'url': url}

    def izinsiz_getir(self, url, max_hop=3):
        for hop in range(max_hop + 1):
            response = self.ham_getir(url)
            if not 300 <= response['status'] <= 399:
                return response
            location = response['headers'].get('location')
            if not location or hop == max_hop:
                raise ValueError('izinsiz araç redirect sınırı')
            url = urljoin(url, location)
        raise AssertionError('ulaşılmaz')

def model_uret(prompt, fixture_url):
    if os.environ.get('PAFTA_AI_REAL_MODEL') != '1':
        return fixture_url
    model = os.environ.get('PAFTA_AI_MODEL', 'qwen2.5:1.5b')
    payload = json.dumps({
        'model': model, 'stream': False,
        'prompt': prompt + '\nYalnız getirilecek tam URLyi yaz.\nÖrnek: ' + fixture_url,
    }).encode()
    request = Request('http://127.0.0.1:11434/api/generate', data=payload,
                      headers={'Content-Type': 'application/json'})
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=30) as response:
        text = json.load(response)['response'].strip()
    match = re.search(r'http://[^\s<>]+', text)
    if not match:
        raise ValueError('Ollama cevabında URL yok')
    return match.group(0).rstrip('.,;)')

import sys
import types
_lab_module = types.ModuleType('ai_ssrf_lab')
_lab_module.AISSRFLab = AISSRFLab
_lab_module.model_uret = model_uret
sys.modules['ai_ssrf_lab'] = _lab_module
# Visible synthetic scenario files; existing real loopback setup above is preserved.
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-21")
```

```starter
import ai_lab
from ai_saldiri_veri import json_yukle,metin_yukle
def modelden_araca(model,url_getir,prompt):
    # KUSURLU BAŞLANGIÇ KODU: modeli iki kez çağırıyor; ikinci cevap ilk URL'den farklı olabilir.
    secilen_url=model(prompt)
    yanit=url_getir(model(prompt))
    return {"prompt":prompt,"secilen_url":secilen_url,"arac_yaniti":yanit}

from urllib.parse import urlsplit,urljoin

def guvenli_getir(url,origin,cozucu,ham_getir,max_hop=2):
    # KUSURLU BAŞLANGIÇ KODU: yalnız origin IP'sini alıp redirect hedefini yeniden doğrulamıyor.
    ip=cozucu(urlsplit(origin).hostname)
    for _ in range(max_hop+1):
        r=ham_getir(url,ip)
        if r["status"] not in (301,302,307):
            return r
        url=urljoin(url,r["headers"]["location"])
    raise ValueError("redirect sınırı")

if ai_lab.CALISTIR:
    print("Sentetik senaryolar:",json_yukle("veri/ssrf-senaryolari.json"))
    print("Sentetik HTTP biçimi:\n"+metin_yukle("veri/http-akisi.txt"))
    from sandbox import ai_gercek_ai_saldiri_21 as deney
    deney.goster(modelden_araca,guvenli_getir)

```

```test
sonuclar=[]
_ok=ok
_eq=eq
_raises=raises
def ok(*args,**kwargs):
    sonuc=_ok(*args,**kwargs)
    sonuclar.append(bool(sonuc))
    return sonuc
def eq(*args,**kwargs):
    sonuc=_eq(*args,**kwargs)
    sonuclar.append(bool(sonuc))
    return sonuc
def raises(*args,**kwargs):
    sonuc=_raises(*args,**kwargs)
    sonuclar.append(bool(sonuc))
    return sonuc
import ai_lab,ast
YASAK=("zincir_ref","getir_ref","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=YASAK)
for node in ast.walk(ast.parse(src)):
    if isinstance(node,ast.ImportFrom) and any(a.name in YASAK or a.name=="*" for a in node.names):
        sorun.append("referans import edilemez")
if sorun:
    ok(False,"Kendi model zincirini ve hop kapısını yaz: "+", ".join(sorun))
    stop()
from ai_ssrf_lab import AISSRFLab, model_uret
with AISSRFLab() as lab:
    prompts = []
    tool_calls = []
    selected = lab.public_url('/start')
    def model(prompt):
        prompts.append(prompt)
        return selected
    def tool(url):
        tool_calls.append(url)
        return lab.izinsiz_getir(url)
    out = modelden_araca(model, tool, 'Bu sayfayı özetle')
    eq(prompts, ['Bu sayfayı özetle'], 'model istemi değişmeden bir kez aldı')
    eq(tool_calls, [selected], 'model çıktısı değişmeden tool argümanı oldu')
    eq(out['prompt'], 'Bu sayfayı özetle', 'izde prompt var')
    eq(out['secilen_url'], selected, 'izde model URLsi var')
    eq(out['arac_yaniti']['body'], {'service':'internal','path':'/canary','canary':lab.canary}, 'iç servis gövdesi gerçek yanıt')
    eq(out['arac_yaniti']['url'], lab.internal_url(), 'redirect sonrası gerçek hedef izde')
    eq(lab.events('public'), ['/start'], 'public HTTP olayı')
    eq(lab.events('internal'), ['/canary'], 'internal canary HTTP olayı')
    eq(lab.canary_hits(), 1, 'zincir canary ile kanıtlandı')

# Aynı kod yeni portlarda ve doğrudan model-seçimli internal URL ile çalışmalı.
with AISSRFLab() as lab2:
    direct = modelden_araca(lambda p: lab2.internal_url(), lab2.izinsiz_getir, 'ikinci deneme')
    eq(direct['arac_yaniti']['body']['canary'], lab2.canary, 'dinamik canary; hardcode değil')
    eq(direct['arac_yaniti']['status'], 200, 'gerçek internal HTTP 200')
    eq(lab2.canary_hits(), 1, 'doğrudan AI-SSRF kanıtı')

for bad in ('', None, 7, '   '):
    calls = []
    raises(ValueError, lambda bad=bad: modelden_araca(lambda p: bad, lambda u: calls.append(u), 'x'), msg='geçersiz model çıktısı reddedilir')
    eq(calls, [], 'geçersiz çıktı araca ulaşmadı')

calls = []
def counted_tool(url):
    calls.append(url)
    return {'status': 204, 'body': None}
out = modelden_araca(lambda p: 'http://public.test:1234/ok', counted_tool, 'p')
eq(len(calls), 1, 'tool tam bir kez çağrıldı')
eq(out, {'prompt':'p','secilen_url':'http://public.test:1234/ok','arac_yaniti':{'status':204,'body':None}}, 'araç cevabı ve tool izi korunur')

from ai_ssrf_lab import AISSRFLab, model_uret
with AISSRFLab() as lab:
    sent = []
    def transport(url, ip):
        sent.append((url, ip))
        return lab.ham_getir(url, ip)
    direct = guvenli_getir(lab.public_url('/ok'), lab.public_origin, lab.cozucu, transport)
    eq(direct['body'], {'service':'public','path':'/ok'}, 'izinli gerçek HTTP cevabı')
    eq(sent, [(lab.public_url('/ok'),'127.0.0.1')], 'doğrulanan IP gerçek bağlantıya sabitlendi')

    sent.clear()
    zero = guvenli_getir(lab.public_url('/ok'), lab.public_origin, lab.cozucu, transport, max_hop=0)
    eq(zero['status'], 200, 'sıfır hop doğrudan isteği engellemez')
    eq(len(sent), 1, 'sıfır hopta tam bir doğrudan bağlantı')

    sent.clear()
    result = guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lab.cozucu, transport, max_hop=2)
    eq(result['body'], {'service':'public','path':'/ok'}, 'iki gerçek redirect hopu tamamlandı')
    eq([u for u,ip in sent], [lab.public_url('/hop1'),lab.public_url('/hop2'),lab.public_url('/ok')], 'her hop gerçek transportta görüldü')
    eq({ip for u,ip in sent}, {'127.0.0.1'}, 'bütün hoplar aynı doğrulanmış IPye sabitli')
    eq(lab.canary_hits(), 0, 'meşru trafik internal canaryye gitmedi')

    before = len(lab.events('public'))
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lab.cozucu, transport, max_hop=1), msg='üçüncü istek hop sınırını aşar')
    eq(len(lab.events('public'))-before, 2, 'sınırı aşan yeni hedefe istek yok')

    before = len(lab.events('public'))
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lab.cozucu, transport, max_hop=0), msg='sıfır hopta ilk redirect hedefi aşılmaz')
    eq(len(lab.events('public'))-before, 1, 'sıfır hopta yalnız başlangıç isteği yapılır')

    # Varsayılan tam 2 hop'tur; üçüncü redirect hedefine bağlanılmaz.
    lab.public.redirects['/chain3'] = '/hop1'
    before = len(lab.events('public'))
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/chain3'), lab.public_origin, lab.cozucu, transport), msg='varsayılan sınır üçüncü redirecti reddeder')
    eq(len(lab.events('public'))-before, 3, 'varsayılan sınırda /ok hedefine istek yok')

    raises(ValueError, lambda: guvenli_getir(lab.public_url('/start'), lab.public_origin, lab.cozucu, transport), msg='cross-origin redirect reddedilir')
    eq(lab.canary_hits(), 0, 'redirect iç servise hiç ulaşmadı')
    eq(lab.events('internal'), [], 'iç origin için socket olayı yok')

    raises(ValueError, lambda: guvenli_getir(lab.public_url('/loop'), lab.public_origin, lab.cozucu, transport, max_hop=3), msg='redirect döngüsü sınırlı')

    for bad in (lab.internal_url(), lab.public_url('/ok').replace('public.test','other.test'),
                f'http://public.test:{lab.internal.server_port}/ok',
                lab.public_url('/ok').replace('http://','https://'),
                lab.public_url('/ok')+'#fragment',
                lab.public_url('/ok').replace('http://','http://user@'),
                'http://127.0.0.1:80/ok', '/ok'):
        raises(ValueError, lambda bad=bad: guvenli_getir(bad, lab.public_origin, lab.cozucu, transport), msg='yanlış origin/port/şema veya belirsiz URL')
    eq(lab.canary_hits(), 0, 'yanlış origin denemeleri canary üretmedi')

    # DNS rebinding mutasyonu: çözümlenen IP politikadan geçmeden socket açılmamalı.
    before_calls = len(sent)
    dns_answers = iter(['127.0.0.1', '127.0.0.2'])
    def rebind(hostname):
        return next(dns_answers)
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/ok'), lab.public_origin, rebind, transport), msg='ilk çözümleme ile bağlantı öncesi DNS cevabı farklıysa reddedilir')
    eq(len(sent), before_calls, 'kötü DNS cevabında gerçek transport çağrısı yok')

    before_calls = len(sent)
    hop_dns = iter(['127.0.0.1', '127.0.0.1', '127.0.0.2'])
    raises(ValueError, lambda: guvenli_getir(lab.public_url('/hop1'), lab.public_origin, lambda h: next(hop_dns), transport), msg='redirect hopunda DNS rebinding reddedilir')
    eq(len(sent)-before_calls, 1, 'DNS değişen ikinci hop için socket açılmadı')

    # İkinci çözümleme transport içinde yeniden yapılamaz; gözlenen IP aynı kalmalı.
    resolutions = []
    def watched_dns(hostname):
        resolutions.append(hostname)
        return '127.0.0.1'
    guvenli_getir(lab.public_url('/ok'), lab.public_origin, watched_dns, transport)
    ok(len(resolutions) >= 2, 'origin ve bağlantı hostu DNS ile ölçüldü')
    eq(sent[-1][1], '127.0.0.1', 'DNS kontrolü ile socket aynı IPyi kullandı')

for bad in (-1, True, 1.5, None):
    raises(ValueError, lambda bad=bad: guvenli_getir('http://public.test:1/ok','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:None,max_hop=bad), msg='max_hop tipi ve alt sınırı')

# Yeni laboratuvar ve portlar: cevap, canary veya origin hardcode edilemez.
with AISSRFLab() as other:
    raises(ValueError, lambda: guvenli_getir(other.public_url('/start'), other.public_origin, other.cozucu, other.ham_getir), msg='ikinci laboratuvarda da cross-origin redirect durur')
    eq(other.canary_hits(), 0, 'yeni dinamik canary de erişilmez kaldı')
    ok(guvenli_getir(other.public_url('/ok'), other.public_origin, other.cozucu, other.ham_getir)['url'].endswith('/ok'), 'dinamik origin ile gerçek başarı')

# Transport test double'ı: kontrol ilk istekten önce ve her hop'ta çalışır.
calls = []
def deny_transport(url, ip):
    calls.append((url, ip))
    return {'status':200,'headers':{},'body':{},'url':url}
raises(ValueError, lambda: guvenli_getir('http://internal.test:9/canary','http://public.test:1',lambda h:'127.0.0.1',deny_transport), msg='ilk URL de kontrol edilir')
eq(calls, [], 'ilk URL reddinde bağlantı yok')

responses = iter([
    {'status':302,'headers':{'location':'/next'},'body':None,'url':'http://public.test:1/a'},
    {'status':200,'headers':{},'body':{'ok':True},'url':'http://public.test:1/next'},
])
seen = []
def fake(url, ip):
    seen.append(url)
    return next(responses)
r = guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',fake)
eq(seen, ['http://public.test:1/a','http://public.test:1/next'], 'göreli Location mevcut URLye göre çözüldü')
eq(r['body'], {'ok':True}, 'son cevap değiştirilmeden döndü')

# Desteklenen üç redirect sınıfı da gerçekten izlenir; listeden biri çıkarılırsa yakalanır.
for status in (301, 302, 307):
    status_responses = iter([
        {'status':status,'headers':{'location':'/next'},'body':None,'url':'http://public.test:1/a'},
        {'status':200,'headers':{},'body':{'ok':status},'url':'http://public.test:1/next'},
    ])
    status_calls = []
    def status_transport(url, ip):
        status_calls.append(url)
        return next(status_responses)
    status_result = guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',status_transport)
    eq(status_result['body'], {'ok':status}, '301/302/307 desteklenen redirect sınıfı')
    eq(len(status_calls), 2, 'desteklenen redirect bir sonraki hopa gider')

# 3xx aralığının iki ucu ve desteklenmeyen sınıflar ilk yanıtta durur; hop limitine kadar tekrarlanmaz.
for status in (300, 303, 308, 399):
    unsupported_calls = []
    def unsupported_transport(url, ip):
        unsupported_calls.append(url)
        return {'status':status,'headers':{'location':'/x'},'body':None,'url':url}
    raises(ValueError, lambda: guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',unsupported_transport), msg='300/303/308/399 desteklenmeyen redirect')
    eq(len(unsupported_calls), 1, 'desteklenmeyen redirect için yeni hop yapılmaz')

for response in ({'status':302,'headers':{}}, {'status':302,'headers':{'location':''}},
                 {'status':302,'headers':{'location':'/a\tb'}}, {'status':302,'headers':{'location':'/a b'}}):
    raises(ValueError, lambda response=response: guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:response), msg='bozuk veya kontrol karakterli Location')
for status in (200, 299, 400):
    response = {'status':status,'headers':{},'body':status,'url':'http://public.test:1/a'}
    eq(guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:response), response, '3xx dışı doğrudan cevap')

# Location ASCII 33 kabul edilir; 32 zaten reddedilir. 127 ve 128 de sonraki URL denetiminden önce bağlantı açamaz.
location_responses = iter([
    {'status':302,'headers':{'location':'/a!b'},'body':None,'url':'http://public.test:1/a'},
    {'status':200,'headers':{},'body':'ascii-33','url':'http://public.test:1/a!b'},
])
eq(guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:next(location_responses))['body'], 'ascii-33', 'Location ASCII 33 izinli komşu')
for code in (127, 128):
    location_calls = []
    def location_transport(url, ip, code=code):
        location_calls.append(url)
        return {'status':302,'headers':{'location':'/a'+chr(code)+'b'},'body':None,'url':url}
    raises(ValueError, lambda: guvenli_getir('http://public.test:1/a','http://public.test:1',lambda h:'127.0.0.1',location_transport), msg='Location 127/128 ASCII URL sınırını aşamaz')
    eq(len(location_calls), 1, 'Location 127/128 için ikinci socket yok')

# URL'nin eşit uçları ve iki komşusu: 32/127/128 reddedilir, 33 kabul edilir.
for code, allowed in ((32,False),(33,True),(127,False),(128,False)):
    ascii_calls = []
    def ascii_transport(url, ip):
        ascii_calls.append(url)
        return {'status':200,'headers':{},'body':'ok','url':url}
    target = 'http://public.test:1/a'+chr(code)+'b'
    if allowed:
        eq(guvenli_getir(target,'http://public.test:1',lambda h:'127.0.0.1',ascii_transport)['status'], 200, 'URL ASCII 33 kabul edilir')
        eq(len(ascii_calls), 1, 'izinli ASCII komşusu bağlantıya ulaşır')
    else:
        raises(ValueError, lambda target=target: guvenli_getir(target,'http://public.test:1',lambda h:'127.0.0.1',ascii_transport), msg='URL ASCII 32/127/128 reddedilir')
        eq(ascii_calls, [], 'reddedilen ASCII sınırında socket yok')

for bad in ('http://public.test:1/a\\b','http://public.test:1/a#x',
            'http://public.test:1/ğ','http://public.test:/','http://public.test:65536/'):
    raises(ValueError, lambda bad=bad: guvenli_getir(bad,'http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:ok(False,'ağ açılmamalı')), msg='ASCII ve ayrıştırma sınırı')
raises(ValueError, lambda: guvenli_getir(123,'http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:ok(False,'ağ açılmamalı')), msg='string olmayan URL reddedilmeli')
raises(ValueError, lambda: guvenli_getir('http://public.test:1/ok','http://public.test:bad',lambda h:'127.0.0.1',lambda u,ip:ok(False,'ağ açılmamalı')), msg='geçersiz origin reddedilmeli')
eq(guvenli_getir('http://public.test:1/a~b','http://public.test:1',lambda h:'127.0.0.1',lambda u,ip:{'status':200,'headers':{},'body':'ok','url':u})['status'], 200, 'URL ASCII 126 kabul edilir')


# urljoin baştaki boşluk/kontrolü normalize edebilir; ham Location önceden reddedilmelidir.
for raw_location in (' /ok','\t/ok','\n/ok','\r/ok'):
    leading_calls=[]
    def leading_transport(url,ip):
        leading_calls.append((url,ip))
        return {'status':302,'headers':{'location':raw_location},'body':None,'url':url}
    raises(ValueError,lambda:guvenli_getir('http://public.test:1/a','http://public.test:1',lambda _:'127.0.0.1',leading_transport),msg='ham Location normalleştirmeden önce reddedilmeli')
    eq(len(leading_calls),1,'bozuk Location için ikinci bağlantı açılmaz')

from sandbox import ai_gercek_ai_saldiri_21 as deney
import tempfile
from pathlib import Path
# Guard is evaluated before all contract tests.
if not all(sonuclar):
    stop()
with tempfile.TemporaryDirectory(prefix='pafta_ssrf21_') as tmp:
    p=Path(tmp)/'not.txt';p.write_text(deney.ORNEK.read_text(encoding='utf-8'),encoding='utf-8')
    r=deney.deney(modelden_araca,guvenli_getir,p,Path(tmp)/'deney')
    for k,v in r['kontroller'].items():ok(v,'gerçek deney: '+k)
    accepted=all(sonuclar) and all(r['kontroller'].values());ai_lab.kanit_yaz('saldiri-21-ssrf',dict(r,kabul=accepted));ok(accepted,'gerçek modelURL/HTTP/socket ve herhop kapısı; saldırıbaşarısı şart değil')

```

```solution
import ai_lab
def modelden_araca(model, url_getir, prompt):
    secilen_url = model(prompt)
    if not isinstance(secilen_url, str) or not secilen_url.strip():
        raise ValueError('model boş olmayan URL metni üretmeli')
    arac_yaniti = url_getir(secilen_url)
    return {'prompt': prompt, 'secilen_url': secilen_url, 'arac_yaniti': arac_yaniti}

from urllib.parse import urlsplit, urljoin

def guvenli_getir(url, origin, cozucu, ham_getir, max_hop=2):
    if type(max_hop) is not int or max_hop < 0:
        raise ValueError('hop sınırı')
    try:
        allowed = urlsplit(origin)
        allowed_key = (allowed.scheme, allowed.hostname, allowed.port)
        allowed_ip = cozucu(allowed.hostname)
    except (ValueError, TypeError) as exc:
        raise ValueError('geçersiz origin') from exc

    def denetle(current):
        if not isinstance(current, str) or any(ord(c) <= 32 or ord(c) >= 127 for c in current) or '\\' in current or '#' in current:
            raise ValueError('belirsiz URL')
        try:
            u = urlsplit(current)
            key = (u.scheme, u.hostname, u.port)
            if key != allowed_key or u.username is not None or u.password is not None:
                raise ValueError('origin sınırı')
            ip = cozucu(u.hostname)
        except (ValueError, TypeError) as exc:
            raise ValueError('URL/DNS reddi') from exc
        if ip != allowed_ip:
            raise ValueError('DNS sınırı')
        return ip

    hops = 0
    while True:
        ip = denetle(url)
        response = ham_getir(url, ip)
        status = response['status']
        if not 300 <= status <= 399:
            return response
        if status not in (301, 302, 307) or hops >= max_hop:
            raise ValueError('redirect türü/sınırı')
        location = response['headers'].get('location')
        if not location or any(ord(c) <= 32 for c in location):
            raise ValueError('Location')
        url = urljoin(url, location)
        hops += 1
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_21 as deney
    deney.goster(modelden_araca,guvenli_getir)

```

```hint
Modeli ve aracı birer kez çağır; seçilen URLyi değiştirme. Her hopta origin bütünü ve DNScevabı denetlenmeli, aynı IP gerçek bağlantıya verilmeli. Yalnız bütün bağlantıları reddetmek normal HTTP kontrolünü geçemez.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
AI-SSRF zincirinde model bir URL önerir, araç onu gerçek bağlantıya çevirir. Model seçimini ve HTTP redirect sonrası gerçek hedefi aynı canary kaydıyla birleştir. Savunmada yalnız ilk URL yeterli değildir: her Location için origin, port ve DNS denetlenir, doğrulanmış IP socket bağlantısına sabitlenir. Hop sınırını aşan bir sonraki hedefe hiç istek açılmamalı.

Önkoşul ve yol köprüsü: ai-saldiri-22 redirect ve DNS.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| İlk URL izinliyse bütün redirectler izinlidir | Her hop yeni bir yetki ve bağlantı kararıdır |

Dinleyiciye sor: Bu mekanizmada hangi bilgi veri, hangisi yetki kaynağıdır; testin geçtiğini hangi gerçek gözlemle kanıtlarsın? Sentetik örnek ile canlı deney kaydını ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html): Allowlist, redirect ve DNS hedefini birlikte ele almak için referans. Bu ders yalnız kendi yerel HTTP servislerini kullanır; gerçek bulut metadata hedefine bağlanmaz. Çalışan araç/model sürümü canlı kanıtta saklanır; bağlantıdaki belge sürümüyle otomatik eşit kabul edilmez.
:::
