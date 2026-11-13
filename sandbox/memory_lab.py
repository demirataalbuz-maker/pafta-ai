# -*- coding: utf-8 -*-
"""PU04: çevrimdışı bellek dışa aktarımları ve açık onaylı gerçek araçlar.

Sentetik sınav verisi tracks/purple/fixtures/pu04 altındadır. Buradaki yardımcılar
yalnız CSV/JSON okur ve alan dönüşümü yapar; dersin ilişkilendirme görevlerini çözmez.

Gerçek toplama asla örtülü olarak çalışmaz::

    python sandbox/memory_lab.py                         # sentetik fixture durumu
    python sandbox/memory_lab.py volatility --onay --ikili /yol/vol.py --imaj /yol/imaj.raw --cikti /yol/cikti
    python sandbox/memory_lab.py memprocfs --onay --imaj /yol/imaj.raw --cikti /yol/cikti

MemProcFS için önceden kurulmuş ``memprocfs`` Python modülü gerekir. Paket kurulmaz,
imaj indirilmez, canlı sistem açılmaz, süreç belleği ya da kimlik bilgisi okunmaz.
"""
import argparse
import csv
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tracks", "purple", "fixtures", "pu04")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BOSLAR = {"", "-", "--", "n/a", "na", "none", "null", "***"}


def hazirla(hedef="bellek"):
    """Dersin küçük sentetik dosyalarını çalışma klasörüne kopyala."""
    os.makedirs(hedef, exist_ok=True)
    for ad in os.listdir(FIXTURE):
        if ad.lower().endswith((".csv", ".json")):
            shutil.copyfile(os.path.join(FIXTURE, ad), os.path.join(hedef, ad))
    return hedef


def satirlari_oku(yol):
    """CSV, JSON dizisi veya Volatility JSON renderer çıktısından satır sözlükleri."""
    with open(yol, encoding="utf-8-sig", newline="") as f:
        if yol.lower().endswith(".csv"):
            return list(csv.DictReader(f))
        veri = json.load(f)
    if isinstance(veri, dict):
        veri = veri.get("rows", veri.get("Rows", [veri]))
    if not isinstance(veri, list):
        raise ValueError(f"{yol}: JSON dizisi ya da rows nesnesi bekleniyor")
    satirlar = []

    def gez(dugumler):
        for r in dugumler:
            if not isinstance(r, dict):
                continue
            satir = {k: v for k, v in r.items() if k != "__children"}
            if satir:
                satirlar.append(satir)
            cocuklar = r.get("__children", [])
            if isinstance(cocuklar, list):
                gez(cocuklar)

    gez(veri)
    return satirlar


def metin(deger):
    if deger is None:
        return ""
    s = str(deger).strip()
    return "" if s.lower() in BOSLAR else s


def sayi(deger):
    """Onluk ya da 0x önekli PID/adres/port; boş alanlar None olur."""
    s = metin(deger)
    if not s:
        return None
    return int(s, 16) if s.lower().startswith(("0x", "+0x", "-0x")) else int(s, 10)


def evet(deger):
    if isinstance(deger, bool):
        return deger
    if isinstance(deger, (int, float)):
        return bool(deger)
    s = metin(deger).lower()
    if s in ("true", "yes", "1", "evet"):
        return True
    if s in ("false", "no", "0", "hayir", "hayır"):
        return False
    raise ValueError(f"Boolean bekleniyor: {deger!r}")


def zaman(deger):
    """Bilinen UTC yazımlarını ``YYYY-AA-GG SS:DD:ss`` biçimine getir."""
    s = metin(deger)
    if not s:
        return ""
    s = s.replace(" UTC", "").replace("Z", "+00:00")
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        t = dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    if t.tzinfo is not None:
        t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return t.strftime("%Y-%m-%d %H:%M:%S")


def alan(satir, *adlar, varsayilan=""):
    """Farklı araçların alan adlarından ilk dolu olanı döndür."""
    for ad in adlar:
        if ad in satir:
            deger = metin(satir[ad])
            if deger:
                return deger
    return varsayilan


def _sonuc(durum, calisti, arac, neden="", dosyalar=None):
    return {"durum": durum, "calisti": bool(calisti), "arac": arac,
            "neden": neden, "dosyalar": dosyalar or []}


def gereksinim(arac, ikili=None, imaj=None, modul=None):
    """Eksik gereksinimi açıkla; hiçbir aracı çalıştırma."""
    if not imaj or not os.path.isfile(imaj):
        return "Salt okunur, yerel bir bellek imajı gerekli; imaj bulunamadı"
    if arac == "volatility":
        if not ikili or not os.path.isfile(ikili):
            return "Volatility 3 vol.py veya çalıştırılabilir dosyası bulunamadı"
    elif arac == "memprocfs":
        if modul is None and importlib.util.find_spec("memprocfs") is None:
            return "Kurulu memprocfs Python modülü bulunamadı; paket kurulmayacak"
    else:
        return "Araç volatility veya memprocfs olmalı"
    return ""


def volatility_topla(ikili, imaj, cikti, onay=False, timeout=180):
    """Volatility 3 pslist/netscan/malfind JSON; yalnız açık ``onay=True`` ile."""
    if not onay:
        return _sonuc("gereksinim-yok", False, "volatility",
                      "Gerçek araç çalıştırılmadı; açık onay ve yerel imaj gerekli")
    sorun = gereksinim("volatility", ikili, imaj)
    if sorun:
        return _sonuc("atlandi", False, "volatility", sorun)
    os.makedirs(cikti, exist_ok=True)
    komut0 = [sys.executable, os.path.abspath(ikili)] if ikili.lower().endswith(".py") else [os.path.abspath(ikili)]
    dosyalar = []
    for kisa, eklenti in (("pslist", "windows.pslist.PsList"),
                          ("netscan", "windows.netscan.NetScan"),
                          ("malfind", "windows.malfind.Malfind")):
        hedef = os.path.join(cikti, f"volatility_{kisa}.json")
        komut = komut0 + ["-q", "-f", os.path.abspath(imaj), "-r", "json", eklenti]
        try:
            p = subprocess.run(komut, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=timeout, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            return _sonuc("hata", False, "volatility", f"{eklenti}: {e}", dosyalar)
        if p.returncode:
            mesaj = p.stderr.decode("utf-8", "replace").strip()[-1000:]
            return _sonuc("hata", True, "volatility", f"{eklenti}: {mesaj or p.returncode}", dosyalar)
        try:
            veri = json.loads(p.stdout.decode("utf-8-sig"))
        except (UnicodeError, ValueError) as e:
            return _sonuc("hata", True, "volatility", f"{eklenti}: geçerli JSON yok ({e})", dosyalar)
        with open(hedef, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        dosyalar.append(hedef)
    return _sonuc("tamam", True, "volatility", dosyalar=dosyalar)


def memprocfs_topla(imaj, cikti, onay=False, modul=None):
    """MemProcFS API'den yalnız süreç/ağ/VAD meta verisi; bellek baytı okumaz."""
    if not onay:
        return _sonuc("gereksinim-yok", False, "memprocfs",
                      "Gerçek araç çalıştırılmadı; açık onay ve yerel imaj gerekli")
    sorun = gereksinim("memprocfs", imaj=imaj, modul=modul)
    if sorun:
        return _sonuc("atlandi", False, "memprocfs", sorun)
    try:
        mp = modul or __import__("memprocfs")
        vmm = mp.Vmm(["-device", os.path.abspath(imaj), "-readonly"])
        surecler = list(vmm.process_list())
        p_rows = [{"pid": p.pid, "ppid": p.ppid, "name": p.name,
                   "path": getattr(p, "pathuser", ""), "state": p.state} for p in surecler]
        n_rows = list(vmm.maps.net())
        v_rows = []
        for p in surecler:
            for v in p.maps.vad():
                row = dict(v)
                row["pid"] = p.pid
                v_rows.append(row)
        os.makedirs(cikti, exist_ok=True)
        dosyalar = []
        for ad, rows in (("memprocfs_processes.json", p_rows),
                         ("memprocfs_net.json", n_rows),
                         ("memprocfs_vads.json", v_rows)):
            hedef = os.path.join(cikti, ad)
            with open(hedef, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
            dosyalar.append(hedef)
        return _sonuc("tamam", True, "memprocfs", dosyalar=dosyalar)
    except Exception as e:
        return _sonuc("hata", True, "memprocfs", f"{type(e).__name__}: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("arac", nargs="?", choices=("volatility", "memprocfs"))
    ap.add_argument("--ikili")
    ap.add_argument("--imaj")
    ap.add_argument("--cikti", default="memory-export")
    ap.add_argument("--onay", action="store_true", help="Yerel imajda gerçek aracı açıkça çalıştır")
    args = ap.parse_args(argv)
    if not args.arac:
        print(json.dumps({"durum": "hazir", "fixture": FIXTURE,
                          "gercek_arac": "gereksinim-yok; --onay ve --imaj gerekli"}, ensure_ascii=False))
        return 0
    if args.arac == "volatility":
        r = volatility_topla(args.ikili or "", args.imaj or "", args.cikti, args.onay)
    else:
        r = memprocfs_topla(args.imaj or "", args.cikti, args.onay)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["durum"] in ("tamam", "atlandi", "gereksinim-yok") else 1


if __name__ == "__main__":
    sys.exit(main())
