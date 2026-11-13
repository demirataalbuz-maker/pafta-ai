# -*- coding: utf-8 -*-
"""Pafta başlatıcısı: sunucuyu açar, Edge'i uygulama penceresi olarak gösterir.

Pencere kapanınca ön yüz nabız göndermeyi bırakır; 40 sn nabız gelmezse sunucu
kendini kapatır. İkinci kez açılırsa çalışan sunucuya yeni pencere açılır.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine.runtime_env import refresh_windows_runtime_env  # noqa: E402
refresh_windows_runtime_env()

from engine.progress import data_dir  # noqa: E402

DATA = data_dir()
if sys.stdout is None or sys.stderr is None:  # pythonw: konsol yok, hataları dosyaya yaz
    _log = open(os.path.join(DATA, "pafta.log"), "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = _log

INSTANCE = os.path.join(DATA, "instance.json")
EDGE_PATHS = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def alive(port, token):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/ping",
                                     headers={"X-Pafta-Token": token})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def open_window(url):
    edge = next((p for p in EDGE_PATHS if os.path.isfile(p)), None)
    if not edge:
        webbrowser.open(url)
        return
    profile = os.path.join(DATA, "edge-profil")
    # Ayrı profil + eklentisiz: sisteme kurulu eklentiler yeni profilde karşılama
    # sekmesi açmasın, uygulama penceresi tek başına gelsin.
    subprocess.Popen([edge, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run",
                      "--no-default-browser-check", "--window-size=1480,940",
                      "--disable-extensions", "--disable-sync", "--disable-background-mode",
                      "--disable-features=Translate,msEdgeSidebarV2"],
                     creationflags=NO_WINDOW)


def main():
    try:
        with open(INSTANCE, encoding="utf-8") as f:
            inst = json.load(f)
        if alive(inst["port"], inst["token"]):
            open_window(f"http://127.0.0.1:{inst['port']}/")
            return
    except (OSError, ValueError, KeyError):
        pass

    import server
    app, httpd = server.start()
    with open(INSTANCE, "w", encoding="utf-8") as f:
        json.dump({"port": app.port, "token": app.token, "pid": os.getpid()}, f)
    app.last_ping = time.time() + 60  # ilk açılışta pencereye zaman tanı
    open_window(f"http://127.0.0.1:{app.port}/")
    try:
        while time.time() - app.last_ping < 40:
            time.sleep(2)
    finally:
        httpd.shutdown()
        try:
            os.remove(INSTANCE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
