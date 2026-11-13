# -*- coding: utf-8 -*-
"""PU16 için çevrimdışı ve salt-okunur sentetik Linux kayıt erişimi.

Komut çalıştırmaz, ağa bağlanmaz, yetki veya dosya özniteliği değiştirmez.
``hazirla`` yalnız ders fixture'ını koşucunun geçici klasörüne kopyalar.
"""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "purple" / "fixtures" / "pu16_linux_privesc" / "lab.json"


def veri_yukle(yol=FIXTURE):
    """Yalnız belirtilen JSON kaydını oku; canlı sistem sorgusu yapma."""
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def hazirla(hedef=None):
    """Fixture'ı ``pu16_lab.json`` adıyla geçici çalışma klasörüne kopyala."""
    hedef = Path(hedef or Path.cwd()) / "pu16_lab.json"
    shutil.copyfile(FIXTURE, hedef)
    return hedef
