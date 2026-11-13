# -*- coding: utf-8 -*-
"""Ağ Tespiti yolunun laboratuvarı (runner: ids; adım meta'sında motor: suricata | zeek).

- Trafik: görevin tarifinden WSL'de Scapy ile sentetik bir PCAP (sandbox/ids_trafik.py).
- Suricata: WSL dağıtımındaki (varsayılan kali-linux) Kali paketi; servisi devre dışıdır, yalnız
  `suricata -r` ile çevrimdışı çalışır. Kural dosyası yalnız kullanıcınınkidir (-S).
- Zeek: resmi zeek/zeek imajı (ZEEK_IMAJ, özetle sabit), ağsız (--network none) ve iş bitince silinen
  bir konteynerde `zeek -C -r` ile.

Her iş kendi geçici klasöründe çalışır; klasör Windows'un geçici dizinindedir ve WSL ile Docker ona
aynı yoldan erişir.

    python sandbox/ids_lab.py        # kurulum durumunu göster
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ZEEK_IMAJ = "zeek/zeek@sha256:70733f4e540ba1608e37e00c6a93d009f79734262c9ec2ba09d90aa9abc16de5"   # 9.0.0
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class IdsHatasi(Exception):
    def __init__(self, msg, satir=None):
        super().__init__(msg)
        self.msg, self.satir = msg, satir


def _dagitim():
    try:
        from sandbox.wsl_process import distro_name
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pafta_wsl_process", os.path.join(HERE, "wsl_process.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        distro_name = mod.distro_name
    return distro_name()


def _calistir(args, timeout=120):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, creationflags=NO_WINDOW)
    coz = lambda b: b.decode("utf-8", "replace").replace("\x00", "")  # noqa: E731
    return p.returncode, coz(p.stdout), coz(p.stderr)


def _wsl(komut, timeout=120):
    return _calistir(["wsl.exe", "--distribution", _dagitim(), "--exec", "bash", "-c", komut], timeout)


def wsl_yolu(yol):
    yol = os.path.abspath(yol)
    surucu, geri = os.path.splitdrive(yol)
    return "/mnt/" + surucu[0].lower() + geri.replace("\\", "/")


def _tirnak(s):
    return "'" + s.replace("'", "'\\''") + "'"


def zeek_imaji():
    """Sabitlenmiş Zeek imajı yerelde varsa onun adı, yoksa None."""
    kod, _, _ = _calistir(["docker", "image", "inspect", ZEEK_IMAJ], 30)
    return ZEEK_IMAJ if kod == 0 else None


def durum():
    sorunlar = []
    try:
        kod, out, _ = _wsl("suricata -V 2>/dev/null; python3 -c 'import scapy' && echo scapy-var", 60)
        if "Suricata version" not in out:
            sorunlar.append("WSL'de Suricata yok (Kali: sudo apt install suricata; servisi: sudo systemctl disable suricata)")
        if "scapy-var" not in out:
            sorunlar.append("WSL'de Scapy yok (Kali: sudo apt install python3-scapy)")
    except (OSError, subprocess.SubprocessError) as e:
        sorunlar.append(f"WSL çalıştırılamadı: {e}")
    try:
        if not zeek_imaji():
            sorunlar.append(f"Zeek imajı yok: docker pull {ZEEK_IMAJ} (Docker Desktop açık olmalı)")
    except (OSError, subprocess.SubprocessError):
        sorunlar.append("Docker çalışmıyor: Docker Desktop'ı aç")
    return sorunlar


class Is:
    """Bir işin geçici klasörü: trafik → PCAP, Suricata ve Zeek."""

    def __init__(self):
        self.klasor = tempfile.mkdtemp(prefix="pafta_ids_")
        shutil.copy(os.path.join(HERE, "ids_trafik.py"), self.klasor)

    def kapat(self):
        shutil.rmtree(self.klasor, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()

    def yol(self, ad):
        return os.path.join(self.klasor, ad)

    def pcap(self, tarif, ad="trafik.pcap"):
        with open(self.yol("tarif.json"), "w", encoding="utf-8") as f:
            json.dump(tarif, f, ensure_ascii=False)
        kod, _, err = _wsl(f"cd {_tirnak(wsl_yolu(self.klasor))} && python3 ids_trafik.py tarif.json {ad}", 120)
        if kod != 0:
            raise IdsHatasi("trafik kaydı üretilemedi: " + err.strip().splitlines()[-1] if err.strip() else "trafik kaydı üretilemedi")
        return ad

    def suricata(self, kurallar, pcap="trafik.pcap"):
        """Kuralları PCAP üzerinde çalıştır → (alarmlar, bütün eve olayları). Kural hatası IdsHatasi olur."""
        if not any(s.strip() and not s.strip().startswith("#") for s in kurallar.splitlines()):
            raise IdsHatasi("kural dosyası boş: en az bir kural yaz (alert ... (msg:...; sid:...;))")
        with open(self.yol("kurallar.rules"), "w", encoding="utf-8", newline="\n") as f:
            f.write(kurallar if kurallar.endswith("\n") else kurallar + "\n")
        cikti = self.yol("suricata")
        shutil.rmtree(cikti, ignore_errors=True)
        os.makedirs(cikti)
        k = _tirnak(wsl_yolu(self.klasor))
        # Suricata yükleyemediği kuralı atlayıp sıfır çıkış koduyla sürer: hata, -v özetinden ve Error satırlarından okunur
        kod, out, err = _wsl(f"cd {k} && TZ=UTC suricata -v -r {pcap} -S kurallar.rules -l suricata -k none "
                             "--runmode single --set unix-command.enabled=no", 120)
        metin = err + out
        hatalar = [ln.split(": ", 2)[-1].strip() for ln in metin.splitlines() if ln.startswith(("Error:", "E:"))]
        ozet = re.search(r"(\d+) rules successfully loaded, (\d+) rules failed", metin)
        if kod != 0 or hatalar or not ozet or int(ozet.group(2)):
            m = re.search(r"at line (\d+)", metin)
            raise IdsHatasi("Suricata kuralı yükleyemedi: " + (" | ".join(hatalar[:3]) or metin.strip()[-300:]),
                            int(m.group(1)) if m else None)
        olaylar = []
        eve = os.path.join(cikti, "eve.json")
        if os.path.exists(eve):
            with open(eve, encoding="utf-8") as f:
                olaylar = [json.loads(s) for s in f if s.strip()]
        return [o for o in olaylar if o.get("event_type") == "alert"], olaylar

    def zeek(self, betik, pcap="trafik.pcap"):
        """Betiği PCAP üzerinde çalıştır → (print çıktısı, {günlük adı: [kayıt]}). Hata IdsHatasi olur."""
        with open(self.yol("betik.zeek"), "w", encoding="utf-8", newline="\n") as f:
            f.write(betik)
        for ad in os.listdir(self.klasor):
            if ad.endswith(".log"):
                os.remove(self.yol(ad))
        imaj = zeek_imaji()
        if not imaj:
            raise IdsHatasi(f"Zeek imajı yok: docker pull {ZEEK_IMAJ}")
        kod, out, err = _calistir(["docker", "run", "--rm", "--network", "none", "-v", f"{self.klasor}:/w", "-w", "/w",
                                   imaj, "zeek", "-C", "-r", pcap, "betik.zeek", "LogAscii::use_json=T"], 180)
        if kod != 0:
            satir = None
            m = re.search(r'betik\.zeek, line (\d+)', err)
            if m:
                satir = int(m.group(1))
            temiz = " | ".join(s.replace("/w/betik.zeek", "betik.zeek") for s in err.strip().splitlines()[:3])
            raise IdsHatasi("Zeek betiği çalışmadı: " + temiz, satir)
        kayitlar = {}
        for ad in sorted(os.listdir(self.klasor)):
            if ad.endswith(".log"):
                with open(self.yol(ad), encoding="utf-8") as f:
                    kayitlar[ad[:-4]] = [json.loads(s) for s in f if s.strip().startswith("{")]
        return out, kayitlar


if __name__ == "__main__":
    s = durum()
    print("\n".join(s) if s else f"Ağ Tespiti laboratuvarı hazır · Zeek imajı {zeek_imaji()}")
