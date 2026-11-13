# -*- coding: utf-8 -*-
"""JavaScript yolunun sabitlenmiş npm paketlerini (Express 5.3.0) .deps/npm'e kurar.

tools/js_bagimliliklar/package-lock.json'daki sürüm ve bütünlük özetleriyle `npm ci` çalışır;
paketlerin kurulum betikleri çalıştırılmaz (--ignore-scripts). JavaScript koşucusu
NODE_PATH ile .deps/npm/node_modules'u arar.

    python tools/js_bagimlilik_kur.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(ROOT, "tools", "js_bagimliliklar")
HEDEF = os.path.join(ROOT, ".deps", "npm")


def main():
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        sys.exit("npm bulunamadı (Node.js kurulumu gerekli).")
    os.makedirs(HEDEF, exist_ok=True)
    for ad in ("package.json", "package-lock.json"):
        shutil.copy(os.path.join(KAYNAK, ad), os.path.join(HEDEF, ad))
    subprocess.run([npm, "ci", "--prefix", HEDEF, "--ignore-scripts", "--no-fund", "--no-audit"], check=True)
    print("kuruldu:", os.path.join(HEDEF, "node_modules"))


if __name__ == "__main__":
    main()
