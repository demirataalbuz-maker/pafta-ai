"""pu26: tespit doğrulama tezgâhı. İzole bir Linux konteynerinde (`pafta-linux-lab`, --network none) önce meşru
gürültü, sonra seçili dosya-tabanlı Atomic Red Team adımları (sentetik, zararsız echo yükleri) strace altında
koşar; konteyner içindeki güvenilir ayrıştırıcı strace çıktısını normalleştirilmiş olaylara çevirir ve her olayı
saldırı/iyi-huylu diye etiketler. Öğrencinin sınıflandırma, atomic-okuma ve kural işlevleri bu GERÇEK telemetriye
uygulanır. Cron tetiklemesi beklenmez; kalıcılığın kurulumu yakalanır. Konteyner her koşuda atılır; ana makinede
hiçbir şey değişmez. Sentetik veri; yalnız kendi başlattığı konteyneri kapatır."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks/purple/fixtures/pu26_tespit"
IMAJ = "pafta-linux-lab:13-1"
YAZMA_BAYRAK = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_APPEND", "O_TRUNC")
CAGRILAR = ("execve", "openat", "chmod", "fchmodat", "renameat2", "unlinkat")
GURULTU_ON = ("/usr/lib", "/lib", "/usr/bin", "/proc", "/sys", "/etc/ld", "/dev")


def hazirla(hedef=None):
    dest = Path(hedef or Path.cwd()) / "tespit"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("ornekler.json", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


# ---------------------------------------------------------------- referanslar
def _gurultu(yol):
    return any(yol.startswith(p) for p in GURULTU_ON) or yol.endswith(".so") or ".so." in yol


def referans_sinifla(olaylar):
    if not isinstance(olaylar, list):
        raise ValueError("olaylar listesi")
    out = []
    try:
        for e in olaylar:
            cagri, comm = e["cagri"], e["comm"]
            if cagri not in CAGRILAR or not isinstance(comm, str) or not comm:
                raise ValueError("olay alanı")
            bayrak = e.get("bayrak") or []
            if not isinstance(bayrak, list) or any(not isinstance(b, str) for b in bayrak):
                raise ValueError("bayrak")
            if cagri == "execve":
                argv = e.get("argv")
                if not isinstance(argv, list) or not argv or any(not isinstance(a, str) for a in argv):
                    raise ValueError("argv")
                yon, hedef = "calistir", argv[0]
            else:
                yol = e.get("yol")
                if not isinstance(yol, str) or not yol:
                    raise ValueError("yol")
                hedef = yol
                if cagri == "openat":
                    yon = "yaz" if any(b in bayrak for b in YAZMA_BAYRAK) else "oku"
                else:
                    yon = "yaz"
            if yon != "calistir" and _gurultu(hedef):
                continue
            out.append({"comm": comm, "yon": yon, "hedef": hedef})
    except (KeyError, TypeError, AttributeError):
        raise ValueError("bozuk olay")
    return out


def referans_atomik(yaml_metni):
    if not isinstance(yaml_metni, str) or not yaml_metni.strip():
        raise ValueError("yaml")
    teknik = None
    m = re.search(r"(?m)^attack_technique:\s*(\S+)", yaml_metni)
    if m:
        teknik = m.group(1).strip().strip('"')
    if not teknik or not re.fullmatch(r"T\d{4}(\.\d{3})?", teknik):
        raise ValueError("teknik")
    out = []
    bloklar = re.split(r"(?m)^- name:", yaml_metni)[1:]
    for blok in bloklar:
        ad = blok.splitlines()[0].strip().strip('"')
        g = re.search(r"(?m)^\s*auto_generated_guid:\s*(\S+)", blok)
        guid = g.group(1).strip() if g else None
        if not ad or not guid or not re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", guid):
            raise ValueError("test başlığı ya da guid")
        yukseltme = bool(re.search(r"(?m)^\s*elevation_required:\s*true", blok))
        c = re.search(r"(?m)^(?P<ind>[ \t]*)command:[ \t]*\|[ \t]*\n(?P<govde>(?:(?P=ind)[ \t]+.*\n?)+)", blok)
        if not c:
            raise ValueError("komut")
        satirlar = [s.strip() for s in c.group("govde").splitlines() if s.strip()]
        out.append({"teknik": teknik, "ad": ad, "guid": guid, "yukseltme": yukseltme, "komut": satirlar})
    if not out:
        raise ValueError("test yok")
    if len({t["guid"] for t in out}) != len(out):
        raise ValueError("yinelenen guid")
    return sorted(out, key=lambda t: t["guid"])


def referans_kural(sinifli, kural):
    if not isinstance(kural, dict) or not isinstance(kural.get("id"), str) or not kural["id"]:
        raise ValueError("kural id")
    if kural.get("kosul") not in ("hepsi", "herhangi"):
        raise ValueError("koşul")
    secim = kural.get("secim")
    if not isinstance(secim, dict) or not secim:
        raise ValueError("seçim")
    for alan, degerler in secim.items():
        if alan not in ("comm", "yon", "hedef_icerir") or not isinstance(degerler, list) or not degerler \
                or any(not isinstance(d, str) or not d for d in degerler):
            raise ValueError("seçim alanı")
    if not isinstance(sinifli, list):
        raise ValueError("sınıflı olaylar listesi")
    hepsi = kural["kosul"] == "hepsi"
    out = []
    for e in sinifli:
        if not isinstance(e, dict) or e.get("yon") not in ("oku", "yaz", "calistir") \
                or not isinstance(e.get("comm"), str) or not isinstance(e.get("hedef"), str):
            raise ValueError("sınıflı olay alanı")
        sonuc = []
        for alan, degerler in secim.items():
            if alan == "comm":
                sonuc.append(e["comm"] in degerler)
            elif alan == "yon":
                sonuc.append(e["yon"] in degerler)
            else:
                sonuc.append(any(d in e["hedef"] for d in degerler))
        if (all(sonuc) if hepsi else any(sonuc)):
            out.append({"kural": kural["id"], "comm": e["comm"], "yon": e["yon"], "hedef": e["hedef"]})
    return out


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json", "re") for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (
                n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                or n.module == "purple_tespit_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr",
                                                "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) for x in n.targets):
            return False
    return True


# ---------------------------------------------------------------- konteyner tezgâhı
# Konteyner içinde çalışan ayrıştırıcı: strace loglarını normalleştirilmiş olaylara çevirir, etiketler.
# Yalnız bu güvenilir kod ham strace'i ayrıştırır; öğrenci normalleştirilmiş olaylarla çalışır.
WRAPPER = r'''
import json, re, subprocess, os
CALL = ["execve", "openat", "chmod", "fchmodat", "renameat2", "unlinkat"]
# ~ = /root (konteyner kök çalışır). Meşru okumanın bir dosyası olsun diye önce .bashrc'yi var et.
open("/root/.bashrc", "a").close()
# (etiket, teknik, kabuk komutu). "iyi" = meşru gürültü. Hepsi sentetik, zararsız echo yükleri.
GRUPLAR = [
    ("iyi", None, "cat ~/.bashrc >/dev/null; ls -la ~ >/dev/null; echo gunluk > ~/notlar.txt; cat /etc/hostname >/dev/null"),
    ("saldiri", "T1546.004", "echo 'echo pafta-atomic-T1546' >> ~/.bashrc"),
    ("saldiri", "T1053.003", "echo '* * * * * root /bin/echo kalici' > /etc/cron.d/pafta-art"),
    ("saldiri", "T1087.001", "grep 'x:0:' /etc/passwd > /tmp/uid0.txt"),
    ("saldiri", "T1070.003", "rm -f ~/.bash_history; : > ~/.bash_history"),
]
LINE = re.compile(r"^(\d+)\s+[\d.]+\s+(\w+)\((.*)\)\s+=\s+(-?\d+)(?:\s+\w+)?\s*$")
def parse(path):
    ev, comm = [], {}  # comm: pid -> program adı (izden türetilir)
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = LINE.match(ln.rstrip("\n"))
        if not m:
            continue
        pid, call, args, ret = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
        if call not in CALL or ret < 0:  # yalnız başarılı çağrı
            continue
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', args)
        e = {"pid": pid, "comm": comm.get(pid, "bash"), "cagri": call, "yol": None, "argv": None, "bayrak": []}
        if call == "execve":
            am = re.search(r'\[(.*?)\]', args)
            e["argv"] = re.findall(r'"((?:[^"\\]|\\.)*)"', am.group(1)) if am else (parts[:1] or None)
            if not e["argv"]:
                continue
            comm[pid] = e["argv"][0].rsplit("/", 1)[-1]
            e["comm"] = comm[pid]
        else:
            e["yol"] = parts[0] if parts else None
            e["bayrak"] = re.findall(r"O_[A-Z]+", args)
            if e["yol"] is None:
                continue
        ev.append(e)
    return ev
olaylar, etiket, atomik = [], [], {}
for ad, teknik, komut in GRUPLAR:
    log = "/tmp/iz_%d.log" % len(olaylar)
    subprocess.run(["strace", "-f", "-qq", "-ttt", "-s", "300", "-e", "trace=" + ",".join(CALL),
                    "-o", log, "bash", "-c", komut], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for e in parse(log):
        olaylar.append(e)
        etiket.append(ad == "saldiri")
        if teknik:
            atomik.setdefault(teknik, komut)
print(json.dumps({"olaylar": olaylar, "etiket": etiket, "atomik_komut": atomik}))
'''


class TespitLab:
    def __init__(self):
        self.ad = "pafta-pu26-" + str(os.getpid()) + "-" + str(time.time_ns() % 10 ** 6)
        self.telemetri = None
        self.temizlendi = False
        self._basladi = False

    def __enter__(self):
        if shutil.which("docker") is None:
            raise RuntimeError("docker bulunamadı. Bu ders izole bir Linux konteyneri ister; kurulum onayı gerekir.")
        k = subprocess.run(["docker", "image", "inspect", IMAJ], capture_output=True, text=True)
        if k.returncode != 0:
            raise RuntimeError(f"İmaj yok: {IMAJ}. .deps/linux-lab-build altından kurulmalı (onaylı).")
        p = subprocess.run(
            ["docker", "run", "--rm", "--name", self.ad, "--network", "none",
             "--security-opt", "no-new-privileges", "--pids-limit", "256", "--memory", "512m",
             "-u", "0", "-i", IMAJ, "python3", "-"],
            input=WRAPPER, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
        self._basladi = True
        if p.returncode != 0:
            raise RuntimeError("konteyner hata verdi: " + (p.stderr or p.stdout)[-400:])
        satir = [s for s in p.stdout.splitlines() if s.strip().startswith("{")]
        if not satir:
            raise RuntimeError("telemetri alınamadı: " + p.stdout[-300:])
        self.telemetri = json.loads(satir[-1])
        return self

    def __exit__(self, *a):
        # --rm ile konteyner kendiliğinden gider; yine de garantiye al, yalnız kendi adımızı.
        subprocess.run(["docker", "rm", "-f", self.ad], capture_output=True, text=True)
        k = subprocess.run(["docker", "ps", "-aq", "-f", "name=^" + self.ad + "$"], capture_output=True, text=True)
        self.temizlendi = (k.stdout.strip() == "")


ATOMIK_DOSYA = {"T1546.004": "T1546.004", "T1053.003": "T1053.003", "T1087.001": "T1087.001", "T1070.003": "T1070.003"}
ATOMIK_KOK = ROOT / ".deps/atomic-red-team-a8f00488/atomics"


def calistir(olay_sinifla, atomik_oku, kural_uygula, kabul=False):
    import platform
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu26-tespit",
           "python": platform.python_version(), "cihaz": platform.platform()}
    lab = TespitLab()
    try:
        with lab:
            tel = lab.telemetri
            olaylar, etiket = tel["olaylar"], tel["etiket"]
            rec["olay_sayisi"] = len(olaylar)

            sinif = olay_sinifla(list(olaylar))
            sinif_ref = referans_sinifla(list(olaylar))
            if sinif != sinif_ref:
                raise AssertionError("olay_sinifla gerçek telemetride referanstan farklı")

            # atomic yaml'leri gerçek dosyadan oku
            yamller = {}
            for t, dosya in ATOMIK_DOSYA.items():
                yamller[t] = (ATOMIK_KOK / dosya / (dosya + ".yaml")).read_text(encoding="utf-8")
            testler = {t: atomik_oku(y) for t, y in yamller.items()}
            if any(testler[t] != referans_atomik(y) for t, y in yamller.items()):
                raise AssertionError("atomik_oku referanstan farklı")
            rec["atomik_teknikler"] = sorted(testler)

            # öğrencinin kalıcılık kuralı: kabuk yapılandırması / cron.d dosyasına YAZMA
            kural = {"id": "pafta-kalicilik-yazma", "kosul": "hepsi",
                     "secim": {"yon": ["yaz"], "hedef_icerir": [".bashrc", ".bash_profile", ".profile", "/etc/cron.d/", "/etc/profile"]}}
            # saf kural (hata vitrini): yalnız hedefe bakar, yön'e bakmaz → meşru okumada yanılır
            saf = {"id": "pafta-saf-dosya", "kosul": "herhangi",
                   "secim": {"hedef_icerir": [".bashrc", "/etc/cron.d/", "/etc/passwd"]}}

            vurus = kural_uygula(list(sinif), kural)
            if vurus != referans_kural(list(sinif_ref), kural):
                raise AssertionError("kural_uygula gerçek telemetride referanstan farklı")
            saf_vurus = referans_kural(list(sinif_ref), saf)

            # TP/FP: kuralın vurduğu her olayı comm+hedef ile ham olaya geri bağla, gerçek etiketini al
            def etiketle(vuruslar):
                tp = fp = 0
                for v in vuruslar:
                    saldiri = False
                    for i, e in enumerate(olaylar):
                        h = e["argv"][0] if e["cagri"] == "execve" else e.get("yol")
                        if e["comm"] == v["comm"] and h == v["hedef"]:
                            saldiri = saldiri or etiket[i]
                    tp += saldiri
                    fp += not saldiri
                return tp, fp
            rec["kural_tp"], rec["kural_fp"] = etiketle(vurus)
            rec["saf_tp"], rec["saf_fp"] = etiketle(saf_vurus)
            rec["kural_vurus"] = vurus
            rec["saf_vurus_sayi"] = len(saf_vurus)

            if rec["kural_fp"] != 0 or rec["kural_tp"] < 2:
                raise AssertionError(f"kalıcılık kuralı beklenen TP>=2, FP=0 vermedi: {rec['kural_tp']}/{rec['kural_fp']}")
            if rec["saf_fp"] < 1:
                raise AssertionError("saf kural meşru okumada yanlış pozitif vermeliydi (hata vitrini)")
        rec["kabul"] = bool(kabul)
    except BaseException as e:
        rec["error"] = {"type": type(e).__name__, "msg": str(e)[:500]}
        raise
    finally:
        rec["cleanup"] = lab.temizlendi
        if not lab.temizlendi:
            rec["kabul"] = False
        d = Path(os.environ.get("PAFTA_DATA", str(ROOT / "data"))) / "purple-kanit"
        d.mkdir(parents=True, exist_ok=True)
        out = d / ("pu26-" + str(time.time_ns()) + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("GERÇEK TESPİT (izole konteyner · strace telemetrisi) · "
              + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print("olay:", rec["olay_sayisi"], "· teknikler:", rec.get("atomik_teknikler"))
    print("kalıcılık kuralı TP/FP:", rec["kural_tp"], "/", rec["kural_fp"],
          "· saf kural TP/FP:", rec["saf_tp"], "/", rec["saf_fp"])
    return rec
