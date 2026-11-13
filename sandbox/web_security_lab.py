"""PU05 web güvenliği laboratuvarı; bağımsız, kalıcı ve yalnız loopback.

    python sandbox/web_security_lab.py --port 8770

Mevcut HTTP laboratuvarını değiştirmez. Bütün hesaplar ve kayıtlar sentetiktir.
Dış ağ, veri sızdırma, cookie çalma, reverse shell ve komut yürütme yoktur.
"""
from contextlib import AbstractContextManager
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import argparse
import html
import http.client
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import threading


USERS = {"ayse": "pafta-demo", "can": "pafta-demo"}
CANARY = "<script>window.__paftaCanary=1</script>"
COMMAND_PLANS = {
    "durum": {
        "argv": ("pafta-durum", "--format", "json", "--hedef"),
        "hedefler": ("web01", "web02"),
    },
    "liste": {
        "argv": ("pafta-liste", "--dizin"),
        "hedefler": ("/lab/raporlar", "/lab/arsiv"),
    },
}


def memory_database():
    """Her çağrıda yeni, yalnız bellek içi SQLite veritabanı kur."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE notlar (id INTEGER PRIMARY KEY, yazar TEXT, govde TEXT, zaman TEXT)")
    db.executemany(
        "INSERT INTO notlar VALUES (?, ?, ?, ?)",
        [
            (1, "ayse", "Normal not", "2026-10-19T09:00:00Z"),
            (2, "can", "O'Reilly kaydı", "2026-10-19T09:01:00Z"),
            (3, "ayse", "Yedek notu", "2026-10-19T09:02:00Z"),
        ],
    )
    return db


class DOMModel:
    """textContent ve innerHTML farkını küçük, güvenli bir modelle göster."""

    def __init__(self):
        self.nodes = []
        self.canary = False

    def text(self, value):
        self.nodes.append(("text", str(value)))

    def html(self, value):
        value = str(value)
        self.nodes.append(("html", value))
        if "window.__paftaCanary=1" in value:
            self.canary = True

    def serialized(self):
        return "".join(value if kind == "html" else html.escape(value, quote=True)
                       for kind, value in self.nodes)


class WebSecurityLab(AbstractContextManager):
    def __init__(self, port=0):
        self.lock = threading.RLock()
        self.control = "pu05-reset-only"
        self.sessions = {}
        self.reset()
        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.server.lab = self
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def reset(self):
        with self.lock:
            self.sessions.clear()
            self.documents = {
                1: {"id": 1, "owner": "ayse", "title": "Ayşe taslağı"},
                2: {"id": 2, "owner": "can", "title": "Can taslağı"},
            }
            self.revision = 0

    def snapshot(self):
        with self.lock:
            return deepcopy({"documents": self.documents, "revision": self.revision})

    def request(self, method, path, data=None, cookie=None, headers=None):
        """Gerçek TCP HTTP isteği; hedef her zaman bu labın 127.0.0.1 portu."""
        request_headers = dict(headers or {})
        if cookie is not None:
            request_headers["Cookie"] = cookie
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        try:
            conn.request(method, path, body=body, headers=request_headers)
            response = conn.getresponse()
            raw = response.read()
            content_type = response.getheader("Content-Type", "")
            parsed = (json.loads(raw) if raw and content_type.startswith("application/json")
                      else raw.decode("utf-8"))
            return {
                "status": response.status,
                "headers": {k.lower(): v for k, v in response.getheaders()},
                "body": parsed,
            }
        finally:
            conn.close()

    def login(self, user):
        response = self.request("POST", "/session", {"user": user, "password": USERS[user]})
        if response["status"] != 200:
            raise ValueError("Bilinmeyen sentetik lab hesabı")
        return response["headers"]["set-cookie"].split(";", 1)[0]

    def close(self):
        if self.server is not None:
            port = self.server.server_port
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)
            self.server = None
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError("Lab portu kapanmadı")

    def __exit__(self, *args):
        self.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PaftaPU05/1"

    def log_message(self, *args):
        pass

    def reply(self, status, data, headers=None, kind="application/json; charset=utf-8"):
        raw = (json.dumps(data, ensure_ascii=False).encode("utf-8")
               if kind.startswith("application/json") else data.encode("utf-8"))
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def user(self):
        # Oturum kimliği yalnız bu labın belleğindeki sentetik hesaba bağlanır.
        value = self.headers.get("Cookie", "")
        parts = dict(part.strip().split("=", 1) for part in value.split(";") if "=" in part)
        session = self.server.lab.sessions.get(parts.get("sid", ""))
        return session["user"] if session else None

    def payload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 4096:
                raise ValueError()
            raw = self.rfile.read(length)
            value = json.loads(raw) if raw else {}
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError, json.JSONDecodeError):
            return None

    def route(self):
        lab = self.server.lab
        parsed = urlsplit(self.path)
        path = parsed.path
        method = self.command
        with lab.lock:
            if path == "/_control/reset" and method == "POST":
                if self.headers.get("X-Lab-Control") != lab.control:
                    return self.reply(403, {"error": "control"})
                lab.reset()
                return self.reply(200, {"reset": True})

            if path == "/session" and method == "POST":
                data = self.payload()
                if data is None:
                    return self.reply(400, {"error": "json"})
                if data.get("user") not in USERS or data.get("password") != USERS[data["user"]]:
                    return self.reply(401, {"error": "credentials"})
                # Tahmin edilmesi güç olsun diye değil, oturumları ayırmak için sayaç kullanılır.
                sid = f"pu05-{data['user']}-{len(lab.sessions) + 1}"
                lab.sessions[sid] = {"user": data["user"]}
                return self.reply(200, {"user": data["user"]},
                                  {"Set-Cookie": f"sid={sid}; Path=/; HttpOnly; SameSite=Strict"})

            if path == "/xss" and method == "GET":
                note = parse_qs(parsed.query, keep_blank_values=True).get("note", [CANARY])[0]
                if len(note) > 512:
                    return self.reply(413, {"error": "note limit"})
                mode = parse_qs(parsed.query).get("mode", ["safe"])[0]
                if mode not in ("safe", "raw"):
                    return self.reply(400, {"error": "mode"})
                if mode == "raw":
                    rendered = note
                    script = ""
                else:
                    rendered = ""
                    encoded = (json.dumps(note, ensure_ascii=False)
                               .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
                    script = f"document.getElementById('note').textContent={encoded};"
                page = ("<!doctype html><meta charset=utf-8><title>PU05 XSS</title>"
                        f"<div id=note>{rendered}</div><output id=result></output>"
                        f"<script>{script}document.getElementById('result').dataset.canary="
                        "String(window.__paftaCanary===1);</script>")
                return self.reply(200, page, kind="text/html; charset=utf-8")

            if path == "/api/documents" and method == "GET":
                user = self.user()
                if user is None:
                    return self.reply(401, {"error": "session"})
                records = [deepcopy(row) for row in lab.documents.values() if row["owner"] == user]
                return self.reply(200, {"records": records})

            if path.startswith("/api/documents/") and method in ("GET", "PATCH"):
                user = self.user()
                if user is None:
                    return self.reply(401, {"error": "session"})
                suffix = path.removeprefix("/api/documents/")
                if not suffix.isascii() or not suffix.isdecimal():
                    return self.reply(404, {"error": "document"})
                row = lab.documents.get(int(suffix))
                if row is None:
                    return self.reply(404, {"error": "document"})
                if row["owner"] != user:
                    return self.reply(403, {"error": "owner"})
                if method == "GET":
                    return self.reply(200, deepcopy(row))
                data = self.payload()
                if data is None:
                    return self.reply(400, {"error": "json"})
                title = data.get("title")
                if set(data) != {"title"} or not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
                    return self.reply(422, {"error": "title only; length 1..80"})
                row["title"] = title.strip()
                lab.revision += 1
                return self.reply(200, deepcopy(row))

            if path == "/" and method == "GET":
                return self.reply(200, "<!doctype html><title>PU05</title><h1>Pafta web güvenliği labı</h1>",
                                  kind="text/html; charset=utf-8")
            return self.reply(404, {"error": "route"})

    do_GET = route
    do_POST = route
    do_PATCH = route


def browser_path():
    """Kurulu tarayıcıyı bul; hiçbir şey indirme."""
    candidates = [
        os.environ.get("PAFTA_WEB_BROWSER_PATH"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chromium"),
        shutil.which("google-chrome"),
    ]
    return next((value for value in candidates if value and Path(value).is_file()), None)


def browser_xss(lab):
    """Opt-in gerçek tarayıcı deneyi; yalnız zararsız window.__paftaCanary ölçer."""
    if os.environ.get("PAFTA_WEB_BROWSER") != "1":
        raise RuntimeError("SKIP: gerçek tarayıcı deneyi için PAFTA_WEB_BROWSER=1 gerekir")
    executable = browser_path()
    if not executable:
        raise RuntimeError("SKIP: kurulu Edge/Chromium bulunamadı; güvenli DOM modeli kullanılmalı")
    from urllib.parse import urlencode
    results = {}
    with tempfile.TemporaryDirectory(prefix="pafta_pu05_browser_") as profile:
        for mode in ("raw", "safe"):
            url = lab.base + "/xss?" + urlencode({"mode": mode, "note": CANARY})
            argv = [executable, "--headless=new", "--disable-gpu", "--no-proxy-server",
                    "--disable-background-networking", "--disable-component-update", "--disable-sync",
                    "--disable-extensions", "--no-first-run",
                    f"--user-data-dir={profile}-{mode}", "--dump-dom", url]
            try:
                completed = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                                           errors="replace", timeout=20, check=True,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError(f"Gerçek tarayıcı deneyi çalışmadı: {exc}") from exc
            marker = 'data-canary="true"'
            results[mode] = marker in completed.stdout
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    with WebSecurityLab(args.port) as lab:
        print(json.dumps({"url": lab.base, "reset_header": {"X-Lab-Control": lab.control}}), flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
