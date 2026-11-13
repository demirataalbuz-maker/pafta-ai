# -*- coding: utf-8 -*-
"""PU14 için gerçek .eml biçimindeki sentetik kanıtlara çevrimdışı erişim.

DNS sorgusu, URL açma, ek çalıştırma, ağ, alt süreç veya paket kurulumu yoktur.
Yardımcılar yalnız fixture dosyalarını kopyalar ve standart email parser ile okur.
"""
from email import policy
from email.parser import BytesParser
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "purple" / "fixtures" / "pu14_email_analysis"
DOSYALAR = ("oltalama.eml", "kurumsal.eml", "README.md")


def hazirla(hedef=None):
    """Sentetik kanıtları ``hedef/email_analysis`` altına kopyala."""
    klasor = Path(hedef or Path.cwd()) / "email_analysis"
    klasor.mkdir(parents=True, exist_ok=True)
    for ad in DOSYALAR:
        shutil.copyfile(FIXTURE / ad, klasor / ad)
    return klasor


def eml_yukle(yol):
    """Yerel .eml baytlarını standart parser ile oku; içerik çalıştırma."""
    with Path(yol).open("rb") as akim:
        return BytesParser(policy=policy.default).parse(akim)
