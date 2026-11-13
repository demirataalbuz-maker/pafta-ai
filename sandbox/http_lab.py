"""Opt-in advanced HTTP lab. Loopback only; no changes to the HT01–HT16 lab.

python sandbox/http_lab.py --port 8769
The process survives individual lesson jobs. Ctrl+C closes it; /_control/reset
requires the printed control token. This is a teaching application, not Burp.
"""
from contextlib import AbstractContextManager
from copy import deepcopy
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
import secrets
import sys
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit
import http.client


class Lab(AbstractContextManager):
    def __init__(self, port=0, ssl_context=None):
        self.lock = threading.RLock()
        self.control = secrets.token_urlsafe(24)
        self.reset()
        self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        self.server.daemon_threads = True
        self.server.lab = self
        if ssl_context is not None:
            self.server.socket = ssl_context.wrap_socket(self.server.socket, server_side=True)
        self.base = ('https' if ssl_context else 'http') + '://127.0.0.1:' + str(self.server.server_port)
        self.origin = self.base
        self.cors_wildcard = False
        self.redirects = {}
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def reset(self):
        with self.lock:
            self.sessions = {}
            self.items = {1: {'id': 1, 'owner': 'ayse', 'title': 'A kaydi'},
                          2: {'id': 2, 'owner': 'berk', 'title': 'B kaydi'}}
            self.events = []
            self.revision = 0

    def snapshot(self):
        with self.lock:
            return deepcopy({'items': self.items, 'events': self.events, 'revision': self.revision})

    def request(self, method, path, data=None, cookie=None, headers=None):
        """Actual TCP HTTP, no redirects or proxy/environment inheritance."""
        h = dict(headers or {})
        if cookie is not None:
            h['Cookie'] = cookie
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
        if body is not None:
            h.setdefault('Content-Type', 'application/json')
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        try:
            conn.request(method, path, body=body, headers=h)
            r = conn.getresponse()
            raw = r.read()
            return {'status': r.status, 'headers': {k.lower(): v for k, v in r.getheaders()},
                    'body': json.loads(raw) if raw and r.getheader('Content-Type', '').startswith('application/json') else raw.decode('utf-8')}
        finally:
            conn.close()

    def login(self, user):
        result = self.request('POST', '/session', {'user': user, 'password': 'pafta-demo'})
        if result['status'] != 200:
            raise ValueError('unknown lab user')
        return result['headers']['set-cookie'].split(';', 1)[0]

    def close(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)
            self.server = None

    def __exit__(self, *args):
        self.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'PaftaLab/1'

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Expected when curl rejects the TLS peer or a client leaves early.
            # Other application exceptions still reach the server error log.
            self.close_connection = True

    def log_message(self, *args):
        pass

    def reply(self, status, data, headers=None, kind='application/json; charset=utf-8'):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8') if kind.startswith('application/json') else data.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        for name, value in (headers.items() if isinstance(headers, dict) else headers or []):
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def session(self):
        c = SimpleCookie()
        try:
            c.load(self.headers.get('Cookie', ''))
        except Exception:
            return None
        token = c.get('sid')
        return self.server.lab.sessions.get(token.value) if token else None

    def route(self):
        lab = self.server.lab
        parsed = urlsplit(self.path)
        path = parsed.path
        method = self.command
        if path == '/ws':
            from http_ws_lab import serve
            return serve(self)
        with lab.lock:
            payload = None
            if method in ('POST', 'PATCH'):
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 <= length <= 8192:
                        self.close_connection = True
                        return self.reply(413, {'error': 'body limit'})
                    raw = self.rfile.read(length)
                    payload = json.loads(raw) if raw else {}
                    if not isinstance(payload, dict):
                        raise ValueError()
                except (ValueError, UnicodeError):
                    return self.reply(400, {'error': 'JSON object required'})
            s = self.session()
            event = {'method': method, 'path': path, 'user': s['user'] if s else None}
            lab.events.append(event)
            if path == '/graphql' and method == 'POST':
                if (not isinstance(payload.get('query'),str)
                    or payload.get('variables') is not None and not isinstance(payload['variables'],dict)
                    or payload.get('operationName') is not None and not isinstance(payload['operationName'],str)):
                    return self.reply(400,{'error':'query string, variables object and optional operationName required'})
                from http_graphql_lab import execute
                try:
                    result=execute(lab,s,payload)
                except RuntimeError as exc:
                    return self.reply(503,{'error':str(exc)})
                return self.reply(200,result)
            if path in lab.redirects:
                status, location = lab.redirects[path]
                return self.reply(status, {'redirect': True}, {'Location': location})
            if path == '/secret':
                return self.reply(200, {'role': 'simulated-internal', 'value': 'LAB-ONLY'})
            if path == '/_control/reset' and method == 'POST':
                if self.headers.get('X-Lab-Control') != lab.control:
                    return self.reply(403, {'error': 'control token required'})
                lab.reset()
                return self.reply(200, {'reset': True})
            if path == '/session' and method == 'POST':
                if payload.get('user') not in ('ayse', 'berk') or payload.get('password') != 'pafta-demo':
                    return self.reply(401, {'error': 'credentials'})
                sid = secrets.token_urlsafe(24)
                lab.sessions[sid] = {'user': payload['user'], 'csrf': secrets.token_urlsafe(24)}
                return self.reply(200, {'user': payload['user']}, {'Set-Cookie': f'sid={sid}; Path=/; HttpOnly; SameSite=Lax'})
            if path == '/csrf' and method == 'GET':
                return self.reply(200, {'token': s['csrf']}) if s else self.reply(401, {'error': 'session'})
            if path == '/change' and method == 'POST':
                if not s:
                    return self.reply(401, {'error': 'session'})
                token = self.headers.get('X-CSRF-Token', '')
                if not secrets.compare_digest(token.encode('utf-8'), s['csrf'].encode('utf-8')):
                    return self.reply(403, {'error': 'csrf'})
                value = payload.get('title')
                if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80:
                    return self.reply(422, {'error': 'title length 1..80'})
                lab.revision += 1
                return self.reply(200, {'revision': lab.revision, 'title': value.strip()})
            if path.startswith('/items/') and method in ('GET', 'PATCH'):
                if not s:
                    return self.reply(401, {'error': 'session'})
                suffix = path[len('/items/'):]
                if not suffix.isascii() or not suffix.isdecimal():
                    return self.reply(404, {'error': 'item'})
                item = lab.items.get(int(suffix))
                if not item:
                    return self.reply(404, {'error': 'item'})
                if item['owner'] != s['user']:
                    return self.reply(403, {'error': 'owner'})
                if method == 'PATCH':
                    # This separate JSON API deliberately uses ownership + session;
                    # CSRF token experiments live at /change, not a global bypass.
                    title = payload.get('title')
                    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
                        return self.reply(422, {'error': 'title length 1..80'})
                    item['title'] = title.strip()
                    lab.revision += 1
                return self.reply(200, deepcopy(item))
            if path == '/cors':
                origin = self.headers.get('Origin')
                allowed = origin == lab.origin
                h = {'Vary': 'Origin'}
                if allowed:
                    h.update({'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Credentials': 'true'})
                if lab.cors_wildcard:
                    h.update({'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Credentials': 'true'})
                if method == 'OPTIONS':
                    requested = self.headers.get('Access-Control-Request-Method')
                    fields = {x.strip().lower() for x in self.headers.get('Access-Control-Request-Headers', '').split(',') if x.strip()}
                    if not allowed or requested != 'POST' or not fields <= {'content-type', 'x-pafta'}:
                        return self.reply(403, {'error': 'preflight'}, h)
                    h.update({'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type, X-Pafta'})
                    return self.reply(200, {'preflight': True}, h)
                return self.reply(200, {'readable': True}, h)
            if path == '/cookie/set' and method == 'GET':
                return self.reply(200, {'set': True}, [('Set-Cookie','lax=L; Path=/; SameSite=Lax'), ('Set-Cookie','strict=S; Path=/; SameSite=Strict')])
            if path == '/cookie/check':
                return self.reply(200, {'cookie': self.headers.get('Cookie',''), 'method': method})
            if path == '/echo':
                return self.reply(200, {'method': method, 'data': payload})
            if path == '/':
                html = '''<!doctype html><meta charset="utf-8"><title>Pafta HTTP Lab</title>
<h1>Pafta Bilet Masası — kalıcı laboratuvar</h1>
<p>ayse veya berk / pafta-demo. Yalnız kendi laboratuvar hesabını kullan.</p>
<form id="login"><input name="user" value="ayse"><input name="password" value="pafta-demo"><button>Oturum aç</button></form>
<button id="item">1 numaralı kaydı oku</button><pre id="out"></pre>
<script>login.onsubmit=async e=>{e.preventDefault();out.textContent=await(await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(login)))})).text()};
item.onclick=async()=>out.textContent=await(await fetch('/items/1')).text();</script>'''
                return self.reply(200, html, kind='text/html; charset=utf-8')
            return self.reply(404, {'error': 'route'})

    do_GET = route
    do_POST = route
    do_PATCH = route
    do_OPTIONS = route


def main():
    local_deps = Path(__file__).resolve().parents[1]/'.deps'
    if local_deps.is_dir():
        sys.path.insert(0,str(local_deps))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8769)
    parser.add_argument('--tls', action='store_true', help='ephemeral private CA; does not change system trust')
    parser.add_argument('--allow-origin', help='CORS exact allowed origin, e.g. http://127.0.0.1:8769')
    parser.add_argument('--cors-wildcard', action='store_true', help='deliberate wildcard/credential teaching case')
    args = parser.parse_args()
    if args.tls:
        from http_tls_lab import TLSLab
        factory=TLSLab
    else:
        factory=Lab
    with factory(args.port) as lab:
        if args.allow_origin:
            lab.origin=args.allow_origin
        lab.cors_wildcard=args.cors_wildcard
        config={'url': lab.base, 'reset_header': {'X-Lab-Control': lab.control}}
        if args.tls:
            config.update(ca=lab.ca,verified_name='app.pafta.test')
        print(json.dumps(config, ensure_ascii=False), flush=True)
        try:
            # Timed waits let older Windows Python versions dispatch Ctrl+C.
            stop = threading.Event()
            while not stop.wait(0.25):
                pass
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
