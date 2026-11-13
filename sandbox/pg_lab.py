# -*- coding: utf-8 -*-
"""SQL yolunun gerçek PostgreSQL laboratuvarı (adım meta'sında motor: postgres).

PostgreSQL WSL dağıtımında (varsayılan kali-linux) kuruludur; açılışta başlamaz.
Her PostgreSQL işinden önce küme denetlenir, kapalıysa root olarak başlatılır (WSL,
açık oturum kalmayınca dağıtımı durdurur; küme onunla kapanır). WSL'in varsayılan
kullanıcısı için (peer kimlik doğrulamasıyla bağlanan) süper kullanıcı rolü bir kez
oluşturulur. Her iş kendi geçici veritabanını ve rollerini kurar, iş
bitince siler (sandbox/py_harness.py → do_pg_*).

Elle hazırlamak ya da durumu görmek için:  python sandbox/pg_lab.py
"""
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from sandbox.wsl_process import NO_WINDOW, distro_name  # noqa: E402

_kilit = threading.Lock()
_hazir = False


def _wsl(args, root=False, timeout=60):
    cmd = ["wsl.exe", "--distribution", distro_name()]
    if root:
        cmd += ["--user", "root"]
    cmd += ["--exec"] + args
    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, creationflags=NO_WINDOW)
    cozul = lambda b: b.decode("utf-8", "replace").replace("\x00", "")  # noqa: E731
    return p.returncode, cozul(p.stdout), cozul(p.stderr)


def kumeler():
    """pg_lsclusters → [(sürüm, ad, port, durum)]."""
    kod, out, _ = _wsl(["pg_lsclusters", "--no-header"])
    if kod != 0:
        return []
    return [tuple(s.split()[:4]) for s in out.splitlines() if len(s.split()) >= 4]


def available():
    try:
        return bool(kumeler())
    except (OSError, subprocess.SubprocessError):
        return False


def hazirla():
    """Kümeyi gerekirse başlat ve WSL kullanıcısının rolünü kur. Sorun yoksa None, varsa açıklama."""
    global _hazir
    with _kilit:
        try:
            liste = kumeler()
            if not liste:
                return "WSL'de PostgreSQL kümesi bulunamadı (pg_lsclusters boş). Kali'de: sudo apt install postgresql"
            surum, ad, _, durum = liste[0]
            if durum != "online":
                kod, _, err = _wsl(["pg_ctlcluster", surum, ad, "start"], root=True, timeout=90)
                if kod != 0:
                    return f"PostgreSQL {surum}/{ad} başlatılamadı: {err.strip()[-300:]}"
            if _hazir:
                return None
            kod, kullanici, _ = _wsl(["id", "-un"])
            kullanici = kullanici.strip()
            if kod != 0 or not re.fullmatch(r"[a-z_][a-z0-9_-]*", kullanici):
                return f"WSL kullanıcısı okunamadı: {kullanici!r}"
            kod, var, err = _wsl(["/usr/sbin/runuser", "-u", "postgres", "--", "psql", "-tAc",
                                  f"SELECT 1 FROM pg_roles WHERE rolname = '{kullanici}'"], root=True)
            if kod != 0:
                return f"PostgreSQL'e bağlanılamadı: {err.strip()[-300:]}"
            if var.strip() != "1":
                kod, _, err = _wsl(["/usr/sbin/runuser", "-u", "postgres", "--", "createuser", "--superuser", kullanici], root=True)
                if kod != 0:
                    return f"{kullanici} rolü oluşturulamadı: {err.strip()[-300:]}"
        except (OSError, subprocess.SubprocessError) as e:
            return f"WSL çalıştırılamadı: {e}"
        _hazir = True
        return None


if __name__ == "__main__":
    sorun = hazirla()
    print(sorun or f"hazır: {kumeler()}")
