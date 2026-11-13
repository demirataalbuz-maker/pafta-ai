# -*- coding: utf-8 -*-
"""PU13 için çevrimdışı Atomic/Caldera sözleşme fixture'ı erişimi.

Komut, ajan, ağ veya alt süreç çalıştırmaz. YAML'ları ayrıştırmaz ve araçların
kurulu olduğunu varsaymaz; yalnız sentetik ders dosyalarını kopyalar.
"""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "purple" / "fixtures" / "pu13_atomic_caldera"
DOSYALAR = (
    "atomic_test.yaml",
    "caldera_ability.yaml",
    "source_contract.json",
    "plan.json",
    "telemetry.jsonl",
    "rules.json",
    "README.md",
)


def hazirla(hedef=None):
    """Sentetik dosyaları ``hedef/emulation`` altına kopyala."""
    klasor = Path(hedef or Path.cwd()) / "emulation"
    klasor.mkdir(parents=True, exist_ok=True)
    for ad in DOSYALAR:
        shutil.copyfile(FIXTURE / ad, klasor / ad)
    return klasor


def json_yukle(yol):
    """Yerel JSON dosyasını oku; komut yürütme veya ağ erişimi yapma."""
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def olaylari_yukle(yol):
    """JSONL biçimindeki sentetik kayıtları satır satır oku."""
    with Path(yol).open(encoding="utf-8") as akim:
        return [json.loads(satir) for satir in akim if satir.strip()]
