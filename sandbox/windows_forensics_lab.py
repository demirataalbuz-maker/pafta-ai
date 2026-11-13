# -*- coding: utf-8 -*-
"""PU15 için çevrimdışı, sentetik Windows adli izi fixture'ları.

Ham hive, Prefetch, MFT veya LNK ayrıştırılmaz; canlı sistem ve Registry okunmaz.
Yalnız ders için elle üretilmiş normalize JSON kayıtları kopyalanır ve okunur.
"""
import datetime as dt
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "purple" / "fixtures" / "pu15_windows_forensics"
DOSYALAR = ("registry.json", "prefetch.json", "mft.json", "lnk.json", "README.md")


def hazirla(hedef=None):
    """Sentetik normalize kanıtları ``hedef/adli`` altına kopyala."""
    klasor = Path(hedef or Path.cwd()) / "adli"
    klasor.mkdir(parents=True, exist_ok=True)
    for ad in DOSYALAR:
        shutil.copyfile(FIXTURE / ad, klasor / ad)
    return klasor


def json_yukle(yol):
    """Yalnız belirtilen yerel JSON fixture'ını oku."""
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def zaman(deger):
    """Z/offset taşıyan ISO zamanını UTC ``YYYY-AA-GG SS:DD:ss`` yap.

    Saat dilimi belirtmeyen değerler yerel saat varsayılarak tahmin edilmez.
    """
    metin = str(deger).strip()
    if metin.endswith("Z"):
        metin = metin[:-1] + "+00:00"
    an = dt.datetime.fromisoformat(metin)
    if an.tzinfo is None or an.utcoffset() is None:
        raise ValueError("Saat dilimi gerekli; UTC veya açık offset kullanın")
    an = an.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return an.strftime("%Y-%m-%d %H:%M:%S")
