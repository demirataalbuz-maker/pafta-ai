# -*- coding: utf-8 -*-
"""PU06 için çevrimdışı, salt-okunur sentetik fixture erişimi.

Bu modül komut çalıştırmaz, ağ bağlantısı açmaz, kimlik bilgisi üretmez veya
sistem yapılandırmasını değiştirmez. ``hazirla`` yalnız ders koşucusunun geçici
çalışma klasörüne fixture kopyalar.
"""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "purple" / "veri" / "pu06_saldiri_zinciri" / "lab.json"


def veri_yukle(yol=FIXTURE):
    """Ders fixture'ını JSON nesnesi olarak oku; başka kaynağa erişme."""
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def hazirla(hedef=None):
    """``pu06_lab.json`` dosyasını geçici çalışma klasörüne kopyala."""
    hedef = Path(hedef or Path.cwd()) / "pu06_lab.json"
    shutil.copyfile(FIXTURE, hedef)
    return hedef
