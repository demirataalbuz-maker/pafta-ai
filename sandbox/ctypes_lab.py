# -*- coding: utf-8 -*-
"""Pafta · ctypes laboratuvarı: küçük C kaynaklarını gerçek derleyicilerle derler.

P82–P83'ün hazırlık blokları bu dosyayı çalıştırır ve `ctlab` modülünü kurar:

    import ctlab
    ctlab.derle(kaynak, "win64-dll")   # → derlenmiş dosyanın Windows yolu
    ctlab.calistir(kaynak, "win32")    # derler, çalıştırır, stdout'u döndürür

Hedefler
--------
win32       i686-w64-mingw32-gcc ile 32 bit Windows programı; Windows onu WOW64 ile çalıştırır
win64       x86_64-w64-mingw32-gcc ile 64 bit Windows programı
linux64     Kali gcc ile 64 bit Linux programı; WSL içinde çalışır
win64-dll   64 bit Windows DLL'i; 64 bit Python ctypes ile yükler
win32-dll   32 bit Windows DLL'i; yalnız dosya olarak incelenir (YR19), 64 bit Python yükleyemez

Derleyiciler WSL'deki Kali dağıtımındadır (varsayılan `kali-linux`, PAFTA_WSL_DISTRO ile
değişir); Windows'a derleyici kurulmaz. Çıktılar kaynağın SHA-256 özetiyle
%TEMP%\\pafta_ctypes_onbellek klasöründe saklanır; aynı kaynak ikinci kez derlenmez.
Kaynaklar yalnız sabit sayı döndüren, dosya ya da ağa dokunmayan zararsız kodlardır.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import threading
import types

DAGITIM = os.environ.get("PAFTA_WSL_DISTRO", "kali-linux")
ONBELLEK = os.path.join(tempfile.gettempdir(), "pafta_ctypes_onbellek")
DERLEYICI = {"win32": ("i686-w64-mingw32-gcc", ".exe", []),
             "win64": ("x86_64-w64-mingw32-gcc", ".exe", []),
             "linux64": ("gcc", "", []),
             "win64-dll": ("x86_64-w64-mingw32-gcc", ".dll", ["-shared"]),
             "win32-dll": ("i686-w64-mingw32-gcc", ".dll", ["-shared"])}
_PENCERESIZ = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _wsl_yolu(yol):
    surucu, kalan = os.path.splitdrive(os.path.abspath(yol))
    return "/mnt/" + surucu.rstrip(":").lower() + kalan.replace("\\", "/")


def derle(kaynak, hedef):
    if hedef not in DERLEYICI:
        raise ValueError(f"Bilinmeyen hedef: {hedef!r}")
    gcc, uzanti, ek = DERLEYICI[hedef]
    os.makedirs(ONBELLEK, exist_ok=True)
    ozet = hashlib.sha256((hedef + "\0" + kaynak).encode("utf-8")).hexdigest()[:20]
    cikti = os.path.join(ONBELLEK, f"{hedef}-{ozet}{uzanti}")
    if os.path.isfile(cikti):
        return cikti
    # Paralel testler aynı kaynağı aynı anda derleyebilir: her süreç kendi geçici adını kullanır
    eki = f"{os.getpid()}-{threading.get_ident()}"
    c = os.path.join(ONBELLEK, f"{hedef}-{ozet}-{eki}.c")
    gecici = os.path.join(ONBELLEK, f"{hedef}-{ozet}-{eki}{uzanti}.yeni")
    with open(c, "w", encoding="utf-8", newline="\n") as f:
        f.write(kaynak)
    try:
        r = subprocess.run(["wsl.exe", "-d", DAGITIM, "--", gcc, "-O0", *ek, "-o", _wsl_yolu(gecici), _wsl_yolu(c)],
                           capture_output=True, timeout=120, creationflags=_PENCERESIZ)
        if r.returncode != 0 or not os.path.isfile(gecici):
            raise RuntimeError(f"{gcc} derleyemedi (Kali'de mingw-w64 ve gcc kurulu olmalı): "
                               + r.stderr.decode("utf-8", "replace")[-400:])
        try:
            os.replace(gecici, cikti)
        except PermissionError:          # başka süreç aynı çıktıyı yazıp kullanıyor: onunki geçerli
            if not os.path.isfile(cikti):
                raise
    finally:
        for yol in (c, gecici):
            try:
                os.remove(yol)
            except OSError:
                pass
    return cikti


def calistir(kaynak, hedef):
    yol = derle(kaynak, hedef)
    komut = ["wsl.exe", "-d", DAGITIM, "--", _wsl_yolu(yol)] if hedef == "linux64" else [yol]
    r = subprocess.run(komut, capture_output=True, timeout=60, creationflags=_PENCERESIZ)
    if r.returncode != 0:
        raise RuntimeError(f"{hedef} programı {r.returncode} ile bitti")
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


m = types.ModuleType("ctlab")
m.__doc__ = __doc__
m.derle, m.calistir, m.HEDEFLER = derle, calistir, tuple(DERLEYICI)
sys.modules["ctlab"] = m
