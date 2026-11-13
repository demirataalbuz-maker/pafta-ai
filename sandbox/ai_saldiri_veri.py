# -*- coding: utf-8 -*-
"""ai-saldiri dersleri için görünür, çevrimdışı sentetik örnek veri dosyaları.

Her dersin ``tracks/ai-saldiri/fixtures/<ders>/`` klasörü çalışma klasörüne kopyalanır
(alt klasörler korunur; ör. ``konusmalar/*.json``). Dosyalar elle yazılmış, küçük ve
sentetiktir; gerçek model yanıtı veya canlı saldırı kaydı değildir. Testler bu dosyalardan
ayrı, öğrencinin görmediği verilerle sınar.
"""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "ai-saldiri" / "fixtures"


def hazirla(ders, hedef=None):
    """``fixtures/<ders>`` içeriğini çalışma klasörüne kopyala ve hedef klasörü döndür."""
    kaynak = FIXTURE / ders
    if not kaynak.is_dir():
        raise FileNotFoundError(f"{ders} için örnek veri klasörü yok: {kaynak}")
    taban = Path(hedef or Path.cwd())
    taban.mkdir(parents=True, exist_ok=True)
    for yol in kaynak.rglob("*"):
        bagil = yol.relative_to(kaynak)
        varis = taban / bagil
        if yol.is_dir():
            varis.mkdir(parents=True, exist_ok=True)
        elif yol.is_file():
            varis.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(yol, varis)
    return taban


def json_yukle(yol):
    """Yalnız belirtilen yerel JSON dosyasını UTF-8 olarak oku."""
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def metin_yukle(yol):
    """Yalnız belirtilen yerel metin dosyasını değiştirmeden oku."""
    with Path(yol).open(encoding="utf-8", newline="") as akim:
        return akim.read()
