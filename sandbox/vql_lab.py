# -*- coding: utf-8 -*-
"""Purple yolunun Velociraptor laboratuvarı (adım meta'sında motor: velociraptor).

Velociraptor'ın resmi Linux sürümü (SURUM, özetle doğrulanmış) .deps/velociraptor'dadır ve WSL'de
`velociraptor query` ile, ağsız ve istemci/sunucu kurulmadan, tek bir VQL sorgusu olarak çalışır.
Görevin hazırlığı çalışma klasöründe `disk/` altında bir dosya ağacı kurar; sorgu o ağacın yoluna
`Kok` değişkeniyle erişir.

    python sandbox/vql_lab.py      # kurulum durumunu göster
"""
import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURUM = "0.77.3"
OZET = "c2c4eb585f16b622cd57de04995a7a13c076ee455bc2a828fd9243cec2ccfed8"   # .gz dosyası
KLASOR = os.path.join(ROOT, ".deps", "velociraptor")
GZ = os.path.join(KLASOR, f"velociraptor-v{SURUM}-linux-amd64.gz")
IKILI = os.path.join(KLASOR, f"velociraptor-v{SURUM}-linux-amd64")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class VqlHatasi(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


def _dagitim():
    return os.environ.get("PAFTA_WSL_DISTRO", "kali-linux").strip() or "kali-linux"


def wsl_yolu(yol):
    yol = os.path.abspath(yol)
    surucu, geri = os.path.splitdrive(yol)
    return "/mnt/" + surucu[0].lower() + geri.replace("\\", "/")


def durum():
    if not os.path.exists(GZ):
        return (f"Velociraptor yok: https://github.com/Velocidex/velociraptor/releases/tag/v{SURUM} "
                f"adresinden velociraptor-v{SURUM}-linux-amd64.gz dosyasını {KLASOR} klasörüne koy")
    with open(GZ, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != OZET:
            return f"{GZ} beklenen sürüm değil (sha256 uyuşmuyor)"
    if not os.path.exists(IKILI):
        import gzip
        import shutil
        with gzip.open(GZ, "rb") as g, open(IKILI, "wb") as f:
            shutil.copyfileobj(g, f)
    return None


def sorgu(vql, kok, timeout=120):
    """VQL'i `Kok` = kok (Windows yolu) ile çalıştır → satırlar [dict]. Hata VqlHatasi olur."""
    sorun = durum()
    if sorun:
        raise VqlHatasi(sorun)
    ikili = wsl_yolu(IKILI)
    komut = ["wsl.exe", "--distribution", _dagitim(), "--exec", "bash", "-c",
             'chmod +x "$1" 2>/dev/null; TZ=UTC "$1" query --format json --env "Kok=$2" "$3" 2>&1',
             "vql", ikili, wsl_yolu(kok), vql]
    p = subprocess.run(komut, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, creationflags=NO_WINDOW)
    out = p.stdout.decode("utf-8", "replace").replace("\x00", "")
    satirlar, hatalar, json_metni = [], [], []
    icinde = False
    for s in out.splitlines():
        if s.startswith("["):
            icinde = True
        if icinde:
            json_metni.append(s)
            if s.startswith("]"):
                icinde = False
                try:
                    satirlar += json.loads("\n".join(json_metni))
                except ValueError:
                    hatalar.append("\n".join(json_metni)[:200])
                json_metni = []
        elif s.strip() and ("ERROR" in s or "Error" in s or "error" in s or "Symbol" in s):
            hatalar.append(s.split("]", 1)[-1].strip() if "]" in s else s.strip())
    if hatalar:
        raise VqlHatasi("VQL: " + " | ".join(dict.fromkeys(hatalar))[:500])
    return satirlar


if __name__ == "__main__":
    s = durum()
    print(s or f"Velociraptor {SURUM} hazır: {IKILI}")
