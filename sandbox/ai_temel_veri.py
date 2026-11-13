# -*- coding: utf-8 -*-
"""ai-temel dersleri için görünür, çevrimdışı örnek veri dosyaları.

Her dersin ``tracks/ai-temel/fixtures/<ders>/`` klasörü çalışma klasörüne ``veri/`` olarak kopyalanır.
Dosyalar elle yazılmış, küçük ve sentetiktir; gerçek araçların yalnız biçimini izler. Model indirilmez,
ağa çıkılmaz. Testler bu dosyalardan ayrı, öğrencinin görmediği verilerle sınar.
"""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "ai-temel" / "fixtures"


def hazirla(ders, hedef=None):
    """``fixtures/<ders>`` içeriğini ``hedef/veri`` altına kopyala ve klasörü döndür."""
    kaynak = FIXTURE / ders
    if not kaynak.is_dir():
        raise FileNotFoundError(f"{ders} için örnek veri klasörü yok: {kaynak}")
    klasor = Path(hedef or Path.cwd()) / "veri"
    klasor.mkdir(parents=True, exist_ok=True)
    for yol in kaynak.iterdir():
        if yol.is_file():
            shutil.copyfile(yol, klasor / yol.name)
    return klasor


def json_yukle(yol):
    """Yalnız belirtilen yerel JSON dosyasını oku."""
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def metin_yukle(yol):
    """Yalnız belirtilen yerel metin dosyasını değiştirmeden oku (satır sonları korunur)."""
    with Path(yol).open(encoding="utf-8", newline="") as akim:
        return akim.read()
