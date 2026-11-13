# -*- coding: utf-8 -*-
"""SQL yolunun gerçek MariaDB laboratuvarı (adım meta'sında motor: mariadb).

MariaDB WSL dağıtımında (varsayılan kali-linux) kuruludur; açılışta başlamaz. Her MariaDB
işinden önce servis denetlenir, kapalıysa root olarak başlatılır. /run/mysqld bir tmpfs
klasörüdür ve WSL yeniden başlayınca silinir; başlatmadan önce yeniden kurulur.
WSL'in varsayılan kullanıcısı için unix_socket ile bağlanan bir hesap bir kez oluşturulur;
yetkisi yalnız adı pafta_ ile başlayan veritabanlarıdır. Her iş kendi veritabanını kurar
ve iş bitince siler (sandbox/py_harness.py → do_my_*).

Elle hazırlamak ya da durumu görmek için:  python sandbox/mariadb_lab.py
"""
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from sandbox.pg_lab import _wsl  # noqa: E402

_kilit = threading.Lock()
_hazir = False


def calisiyor():
    kod, out, _ = _wsl(["systemctl", "is-active", "mariadb"])
    return out.strip() == "active"


def available():
    try:
        kod, _, _ = _wsl(["test", "-x", "/usr/sbin/mariadbd"])
        return kod == 0
    except (OSError, subprocess.SubprocessError):
        return False


def hazirla():
    """Servisi gerekirse başlat ve WSL kullanıcısının hesabını kur. Sorun yoksa None, varsa açıklama."""
    global _hazir
    with _kilit:
        try:
            if not available():
                return "WSL'de MariaDB bulunamadı (/usr/sbin/mariadbd). Kali'de: sudo apt install mariadb-server"
            if not calisiyor():
                kod, _, err = _wsl(["sh", "-c", "install -d -o mysql -g mysql -m 755 /run/mysqld && systemctl start mariadb"],
                                   root=True, timeout=120)
                if kod != 0:
                    return f"MariaDB başlatılamadı: {err.strip()[-300:]}"
            if _hazir:
                return None
            kod, kullanici, _ = _wsl(["id", "-un"])
            kullanici = kullanici.strip()
            if kod != 0 or not re.fullmatch(r"[a-z_][a-z0-9_-]*", kullanici):
                return f"WSL kullanıcısı okunamadı: {kullanici!r}"
            sql = (f"CREATE USER IF NOT EXISTS '{kullanici}'@'localhost' IDENTIFIED VIA unix_socket; "
                   f"GRANT ALL PRIVILEGES ON `pafta\\_%`.* TO '{kullanici}'@'localhost';")
            kod, _, err = _wsl(["mariadb", "-e", sql], root=True)
            if kod != 0:
                return f"{kullanici} hesabı kurulamadı: {err.strip()[-300:]}"
        except (OSError, subprocess.SubprocessError) as e:
            return f"WSL çalıştırılamadı: {e}"
        _hazir = True
        return None


if __name__ == "__main__":
    sorun = hazirla()
    print(sorun or "hazır: MariaDB çalışıyor")
