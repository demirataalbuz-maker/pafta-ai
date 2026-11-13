"""PS27/PS28 offline EVTX tezgahı: sentetik EVT kaydı -> Windows'un kendi EVTX'i.

Yalnız çağıranın çalışma klasörüne yeni dosya yazar; hiçbir canlı kanala,
kayıt defterine ya da sistem günlüğüne dokunmaz. Dönüşümü Windows yapar
(wevtutil epl /lf:true), bu yüzden Get-WinEvent dosyayı gerçek bir EVTX
olarak okur. Sınır: eski EVT'den çevrilen kayıtlarda EventData/Data
öğelerinin Name özniteliği yoktur; alanlara sırayla (Properties[n]) erişilir.
Biçim: https://learn.microsoft.com/en-us/windows/win32/eventlog/event-log-file-format
"""
import os
from pathlib import Path
import struct
import subprocess
import tempfile

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PS = "Microsoft-Windows-PowerShell"
T0 = 1767258000  # 2026-01-01 09:00:00 UTC
# Klasik olay türü -> Windows'un yazdığı Level: 1 -> 2 (Error), 2 -> 3 (Warning), 4 -> 4 (Information)
HATA, UYARI, BILGI = 1, 2, 4


def _wevtutil(*args):
    exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wevtutil.exe"
    if not exe.is_file():
        raise RuntimeError("EVTX tezgahı Windows ve yerleşik wevtutil.exe gerektirir.")
    return subprocess.run([str(exe), *map(str, args)], capture_output=True, timeout=20,
                          creationflags=NO_WINDOW)


def _kayit(no, eid, tur, saniye, kaynak, dizgiler):
    if not 0 <= eid <= 65535 or tur not in (HATA, UYARI, BILGI):
        raise ValueError("EventID 0..65535, tür HATA/UYARI/BILGI olmalı")
    if any("\0" in d for d in dizgiler):
        raise ValueError("Dizgi NUL içeremez")
    adlar = (kaynak + "\0PAFTA-LAB\0").encode("utf-16le")
    veri = "".join(d + "\0" for d in dizgiler).encode("utf-16le")
    yuk = adlar + veri
    yuk += b"\0" * (-len(yuk) % 4)
    boy = 56 + len(yuk) + 4
    zaman = T0 + saniye
    bas = struct.pack("<6I4H6I", boy, 0x654C664C, no, zaman, zaman, eid, tur, len(dizgiler),
                      0, 0, 0, 56 + len(adlar), 0, 0, 0, 0)
    return bas + yuk + struct.pack("<I", boy)


def evtx(yol, satirlar):
    """satirlar: (EventID, tür, T0'dan saniye, kaynak, [dizgiler]). Var olan dosyanın üstüne yazmaz."""
    hedef = Path(yol).resolve()
    if not satirlar:
        with tempfile.TemporaryDirectory(prefix="pafta_bos_", dir=hedef.parent) as klasor:
            tohum = evtx(Path(klasor) / "tohum.evtx", [(1, BILGI, 0, PS, ["tohum"])])
            r = _wevtutil("epl", tohum, hedef, "/lf:true", "/ow:false", "/q:*[System[EventID=65535]]")
            if r.returncode:
                raise RuntimeError(f"Boş EVTX üretilemedi ({r.returncode})")
        return hedef
    kayitlar = b"".join(_kayit(i, *s) for i, s in enumerate(satirlar, 1))
    son = 48 + len(kayitlar)
    n = len(satirlar)
    boyut = max(65536, son + 40)
    bas = struct.pack("<12I", 48, 0x654C664C, 1, 1, 48, son, n + 1, 1, boyut, 0, 0, 48)
    kuyruk = struct.pack("<10I", 40, 0x11111111, 0x22222222, 0x33333333, 0x44444444,
                         48, son, n + 1, 1, 40)
    with tempfile.TemporaryDirectory(prefix="pafta_evt_", dir=hedef.parent) as klasor:
        kaynak = Path(klasor) / "sentetik.evt"
        kaynak.write_bytes((bas + kayitlar + kuyruk).ljust(boyut, b"\0"))
        r = _wevtutil("epl", kaynak, hedef, "/lf:true", "/ow:false")
        if r.returncode:
            raise RuntimeError(f"EVT -> EVTX başarısız ({r.returncode}): "
                               + r.stderr.decode("utf-8", "replace"))
    return hedef


SCM, OTURUM, GUNLUK = "Service Control Manager", "User32", "EventLog"
SISTEM = [
    (6005, BILGI, 0, GUNLUK, []),
    (7036, BILGI, 30, SCM, ["Windows Update", "running"]),
    (7045, BILGI, 60, SCM, ["PaftaYedek", r"C:\Araclar\yedek.exe", "user mode service", "auto start"]),
    (7036, BILGI, 61, SCM, ["PaftaYedek", "running"]),
    (7031, HATA, 120, SCM, ["PaftaYedek", "1", "60000", "1", "Restart the service"]),
    (7036, BILGI, 121, SCM, ["PaftaYedek", "stopped"]),
    (7045, UYARI, 180, SCM, ["Guncelleyici", r"C:\Users\Public\g.exe", "user mode service", "demand start"]),
    (7036, BILGI, 240, SCM, ["Windows Update", "stopped"]),
    (1074, BILGI, 300, OTURUM, ["C:\\Windows\\system32\\shutdown.exe", "PAFTA-LAB", "Planlanmis bakim", "restart"]),
    (6006, BILGI, 301, GUNLUK, []),
]


def ps27():
    evtx("sistem.evtx", SISTEM)
    evtx("bos.evtx", [])
    Path("bozuk.evtx").write_bytes(b"Pafta: bu bir olay gunlugu degil.\n")


def _blok(no):
    return "{6f1e0c2a-%04d-4b5c-9d00-5afe0000%04d}" % (no, no)


# F ile G'nin numaraları bilerek ters: kimliğe göre sıralamak, kayıt sırasına göre sıralamakla aynı sonucu vermesin.
A, B, C, D, E, G, F = (_blok(i) for i in range(1, 8))
DOSYA = r"C:\Betikler"
BETIK = [
    (4105, BILGI, 0, PS, [A, "11111111-2222-3333-4444-555555555555"]),
    (4104, BILGI, 1, PS, ["1", "1", "Get-CimInstance Win32_OperatingSystem |\n    Select-Object Caption, Version",
                          A, DOSYA + r"\envanter.ps1"]),
    (4104, UYARI, 60, PS, ["1", "3", "$istemci = New-Object Net.Web", B, ""]),
    (4104, BILGI, 61, PS, ["1", "2", "Compress-Archive -Path C:\\Veri -Destination ", C, DOSYA + r"\yedek.ps1"]),
    (4104, UYARI, 62, PS, ["2", "3", "Client\n$veri = $istemci.DownloadString('http://rapor.ornek.test/gunluk.txt')\n",
                           B, ""]),
    (4103, BILGI, 63, PS, ["CommandInvocation(Set-Content)", "ParameterBinding(Set-Content)"]),
    (4104, UYARI, 64, PS, ["3", "3", "Set-Content -Path rapor.txt -Value $veri", B, ""]),
    (4104, BILGI, 120, PS, ["1", "1", "Invoke-WebRequest -Uri https://guncelleme.ornek.test/surum.json -OutFile surum.json",
                            D, ""]),
    (4104, BILGI, 180, PS, ["2", "2", "    Remove-Item -WhatIf", E, DOSYA + r"\temizle.ps1"]),
    (4104, BILGI, 181, PS, ["1", "2", "Get-ChildItem $env:TEMP -Filter *.tmp |\n", E, DOSYA + r"\temizle.ps1"]),
    (4104, BILGI, 240, PS, ["1", "1", "Write-Output 'NetXWebClient yalniz bir dosya adi'", F, ""]),
] + [
    # On bir parçalı uzun blok: parça numarası metin olarak sıralanırsa 1, 10, 11, 2 ... olur.
    (4104, BILGI, 300 + i, PS, [str(i), "11", f"# satir {i}" + ("\n" if i < 11 else ""), G, DOSYA + r"\uzun.ps1"])
    for i in range(1, 12)
]


def ps28():
    evtx("betik.evtx", BETIK)
    evtx("bos.evtx", [])
    Path("bozuk.evtx").write_bytes(b"Pafta: bu bir olay gunlugu degil.\n")
