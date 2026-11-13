"""pu23: DevSecOps tezgâhı. Geçici, kasıtlı açıklı küçük bir git deposu kurar; Semgrep (yalnız yerel kural),
gitleaks (git geçmişi) ve Trivy (secret + misconfig, güncelleme kapalı) araçlarını .deps altındaki sabit
sürümlerle paralel koşturur. Ham JSON çıktıları öğrencinin normalize/ölçüm/CI kapısı işlevlerinden geçer.
Sırlar her koşuda rastgele üretilen sahte değerlerdir. Araçlar, her isteği kaydedip 403 dönen yerel bir
vekil üzerinden koşar; dış ağa çıkma denemesi kanıta yazılır. Yalnız kendi geçici klasörünü temizler."""
from datetime import date
from pathlib import Path
import json
import os
import secrets
import shutil
import socketserver
import string
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks/purple/fixtures/pu23_devsecops"
DEPS = ROOT / ".deps"
ARAC = {
    "semgrep": DEPS / "semgrep-venv/Scripts/semgrep.exe",
    "gitleaks": DEPS / "gitleaks-8.30.1/acik/gitleaks.exe",
    "trivy": DEPS / "trivy-0.76.1/acik/trivy.exe",
}
KAPSAM = {"semgrep": ("sast",), "gitleaks": ("sir",), "trivy": ("sir", "yapilandirma")}
TURLER = ("sast", "sir", "yapilandirma")


def hazirla(hedef=None):
    dest = Path(hedef or Path.cwd()) / "devsecops"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("ornekler.json", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


# ---------------------------------------------------------------- referanslar
def _yol(d):
    if not isinstance(d, str) or not d:
        raise ValueError("yol")
    d = d.replace("\\", "/")
    while d.startswith("./"):
        d = d[2:]
    return d


def _tam(x):
    if not isinstance(x, int) or x < 0:
        raise ValueError("satır")
    return x


def _metin(x):
    if not isinstance(x, str) or not x:
        raise ValueError("metin")
    return x


def referans_normalize(arac, ham):
    out = []
    try:
        if arac == "semgrep":
            if not isinstance(ham["results"], list):
                raise ValueError("semgrep")
            for r in ham["results"]:
                out.append({"arac": arac, "kural": _metin(r["check_id"]), "dosya": _yol(r["path"]),
                            "satir": _tam(r["start"]["line"]), "tur": "sast"})
        elif arac == "gitleaks":
            if not isinstance(ham, list):
                raise ValueError("gitleaks")
            for r in ham:
                out.append({"arac": arac, "kural": _metin(r["RuleID"]), "dosya": _yol(r["File"]),
                            "satir": _tam(r["StartLine"]), "tur": "sir"})
        elif arac == "trivy":
            if not isinstance(ham, dict):
                raise ValueError("trivy")
            for res in ham.get("Results") or []:
                hedef = _yol(res["Target"])
                for s in res.get("Secrets") or []:
                    out.append({"arac": arac, "kural": _metin(s["RuleID"]), "dosya": hedef,
                                "satir": _tam(s["StartLine"]), "tur": "sir"})
                for m in res.get("Misconfigurations") or []:
                    if m["Status"] != "FAIL":
                        continue
                    satir = (m.get("CauseMetadata") or {}).get("StartLine") or 0
                    out.append({"arac": arac, "kural": _metin(m["ID"]), "dosya": hedef,
                                "satir": _tam(satir), "tur": "yapilandirma"})
        else:
            raise ValueError("bilinmeyen araç")
    except (KeyError, TypeError, AttributeError) as e:
        raise ValueError("bozuk çıktı: " + type(e).__name__)
    return sorted(out, key=lambda b: (b["dosya"], b["satir"], b["arac"], b["kural"]))


def _oran(a, b):
    return None if b == 0 else round(a / b, 3)


def referans_olc(bulgular, gercek, kapsam):
    if not isinstance(bulgular, list) or not isinstance(gercek, list) or not isinstance(kapsam, dict):
        raise ValueError("tür")
    ids = set()
    for g in gercek:
        if (not isinstance(g, dict) or not isinstance(g.get("id"), str) or g["id"] in ids or g.get("tur") not in TURLER
                or not isinstance(g.get("sorun"), bool) or not isinstance(g.get("dosya"), str)
                or not isinstance(g.get("satir"), int)):
            raise ValueError("gerçek liste")
        ids.add(g["id"])
    for a, t in kapsam.items():
        if not isinstance(t, (list, tuple)) or any(x not in TURLER for x in t):
            raise ValueError("kapsam")
    anahtar = {(g["dosya"], g["satir"], g["tur"]): g for g in gercek}
    sonuc, hat_bulunan, hat_yanlis = {}, set(), 0
    for a in sorted(kapsam):
        bulunan, yanlis = set(), 0
        for b in bulgular:
            if not isinstance(b, dict) or b.get("arac") not in kapsam:
                raise ValueError("bulgu")
            if b["arac"] != a:
                continue
            g = anahtar.get((b["dosya"], b["satir"], b["tur"]))
            if g is not None and g["sorun"]:
                bulunan.add(g["id"])
            else:
                yanlis += 1
        kacan = sorted(g["id"] for g in gercek if g["sorun"] and g["tur"] in kapsam[a] and g["id"] not in bulunan)
        sonuc[a] = {"dogru": len(bulunan), "yanlis": yanlis, "kacan": kacan,
                    "kesinlik": _oran(len(bulunan), len(bulunan) + yanlis),
                    "duyarlilik": _oran(len(bulunan), len(bulunan) + len(kacan))}
        hat_bulunan |= bulunan
        hat_yanlis += yanlis
    kacan = sorted(g["id"] for g in gercek if g["sorun"] and g["id"] not in hat_bulunan)
    sonuc["hat"] = {"dogru": len(hat_bulunan), "yanlis": hat_yanlis, "kacan": kacan,
                    "kesinlik": _oran(len(hat_bulunan), len(hat_bulunan) + hat_yanlis),
                    "duyarlilik": _oran(len(hat_bulunan), len(hat_bulunan) + len(kacan))}
    return sonuc


def _tarih(x):
    if not isinstance(x, str):
        raise ValueError("tarih")
    try:
        return date.fromisoformat(x)
    except ValueError:
        raise ValueError("tarih: " + x)


def referans_ci(bulgular, istisnalar, bugun):
    gun = _tarih(bugun)
    if not isinstance(bulgular, list) or not isinstance(istisnalar, list):
        raise ValueError("tür")
    aktif, dolan, ids = [], [], set()
    for i in istisnalar:
        if not isinstance(i, dict) or any(not isinstance(i.get(k), str) for k in ("id", "arac", "kural", "dosya", "gerekce", "bitis")):
            raise ValueError("istisna")
        if i["id"] in ids or not i["gerekce"].strip():
            raise ValueError("istisna: kimlik ya da gerekçe")
        if "satir" in i and not isinstance(i["satir"], int):
            raise ValueError("istisna satır")
        ids.add(i["id"])
        (aktif if _tarih(i["bitis"]) >= gun else dolan).append(i)
    engel, bastir, kullanilan = [], 0, set()
    for b in bulgular:
        eslesen = [i for i in aktif if (i["arac"], i["kural"], i["dosya"]) == (b["arac"], b["kural"], b["dosya"])
                   and ("satir" not in i or i["satir"] == b["satir"])]
        if eslesen:
            bastir += 1
            kullanilan.update(i["id"] for i in eslesen)
        else:
            engel.append(b)
    return {"gecti": not engel, "engelleyen": sorted(engel, key=lambda b: (b["dosya"], b["satir"], b["arac"], b["kural"])),
            "bastirilan": bastir, "suresi_dolan": sorted(i["id"] for i in dolan),
            "kullanilmayan": sorted(i["id"] for i in aktif if i["id"] not in kullanilan)}


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json",) for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                                                  or n.module == "datetime" and all(a.name == "date" for a in n.names)
                                                  or n.module == "purple_devsecops_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) for x in n.targets):
            return False
    return True


# ---------------------------------------------------------------- kasıtlı açıklı depo
APP = '''import hashlib
import os
import subprocess


def kullanici_bul(db, ad):
    return db.execute("SELECT * FROM k WHERE ad = '" + ad + "'")


def guvenli_bul(db, ad):
    return db.execute("SELECT * FROM k WHERE ad = ?", (ad,))


def yedek_al(dizin):
    return subprocess.run("tar czf yedek.tgz " + dizin, shell=True)


def liste(dizin):
    return subprocess.run(["ls", dizin])


def parola_ozet(p):
    return hashlib.md5(p.encode()).hexdigest()


def onbellek_anahtari(yol):
    return hashlib.md5(yol.encode(), usedforsecurity=False).hexdigest()


def calistir(komut):
    return os.system(komut)
'''
ORNEK = '''# AWS belgelerindeki örnek anahtar; gerçek değil
ORNEK_ANAHTAR = "AKIAIOSFODNN7EXAMPLE"
SAHTE_PAROLA = "changeme"
'''
DOCKERFILE = '''FROM python:latest
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
USER root
CMD ["python", "uygulama/app.py"]
'''
KURALLAR = '''rules:
  - id: sql-birlestirme
    languages: [python]
    severity: ERROR
    message: SQL metni birlestirme ile kuruluyor
    pattern: $DB.execute("..." + $X + "...")
  - id: shell-true
    languages: [python]
    severity: ERROR
    message: shell=True ile komut calistiriliyor
    pattern: subprocess.run(..., shell=True, ...)
  - id: zayif-ozet
    languages: [python]
    severity: WARNING
    message: MD5 ozeti
    pattern: hashlib.md5(...)
'''


def _satir(metin, parca):
    return next(i for i, s in enumerate(metin.splitlines(), 1) if parca in s)


def gercek_liste():
    a = "uygulama/app.py"
    return [
        {"id": "S1", "tur": "sast", "dosya": a, "satir": _satir(APP, "WHERE ad = '\" + ad"), "sorun": True, "not": "SQL birleştirme"},
        {"id": "S2", "tur": "sast", "dosya": a, "satir": _satir(APP, "shell=True"), "sorun": True, "not": "shell=True + girdi"},
        {"id": "S3", "tur": "sast", "dosya": a, "satir": _satir(APP, "md5(p.encode())"), "sorun": True, "not": "parola için MD5"},
        {"id": "S4", "tur": "sast", "dosya": a, "satir": _satir(APP, "os.system"), "sorun": True, "not": "os.system + girdi"},
        {"id": "N1", "tur": "sast", "dosya": a, "satir": _satir(APP, "usedforsecurity=False"), "sorun": False, "not": "önbellek anahtarı, güvenlik amaçlı değil"},
        {"id": "N2", "tur": "sast", "dosya": a, "satir": _satir(APP, "WHERE ad = ?"), "sorun": False, "not": "parametreli sorgu"},
        {"id": "G1", "tur": "sir", "dosya": "uygulama/ayar.py", "satir": 2, "sorun": True, "not": "AWS erişim anahtarı (sahte, rastgele)"},
        {"id": "G2", "tur": "sir", "dosya": "uygulama/ayar.py", "satir": 3, "sorun": True, "not": "AWS gizli anahtarı (sahte, rastgele)"},
        {"id": "G3", "tur": "sir", "dosya": ".env", "satir": 1, "sorun": True, "not": "silinmiş ama git geçmişinde duran token"},
        {"id": "N3", "tur": "sir", "dosya": "tests/ornek_veri.py", "satir": 2, "sorun": False, "not": "AWS belgelerindeki örnek anahtar"},
        {"id": "Y1", "tur": "yapilandirma", "dosya": "Dockerfile", "satir": 1, "sorun": True, "not": ":latest etiketi"},
        {"id": "Y2", "tur": "yapilandirma", "dosya": "Dockerfile", "satir": _satir(DOCKERFILE, "USER root"), "sorun": True, "not": "root kullanıcı"},
        {"id": "Y3", "tur": "yapilandirma", "dosya": "Dockerfile", "satir": 3, "sorun": True, "not": "COPY yerine ADD"},
        {"id": "N4", "tur": "yapilandirma", "dosya": "Dockerfile", "satir": 0, "sorun": False, "not": "HEALTHCHECK yok: işletim konusu, bu politika için güvenlik bulgusu değil"},
    ]


def istisna_liste():
    return [
        {"id": "I1", "arac": "trivy", "kural": "DS-0026", "dosya": "Dockerfile", "gerekce": "Sağlık denetimi orkestratörde yapılıyor", "bitis": "2099-12-31"},
        {"id": "I2", "arac": "semgrep", "kural": "zayif-ozet", "dosya": "uygulama/app.py", "satir": _satir(APP, "usedforsecurity=False"),
         "gerekce": "Önbellek anahtarı; usedforsecurity=False", "bitis": "2099-12-31"},
        {"id": "I3", "arac": "trivy", "kural": "DS-0005", "dosya": "Dockerfile", "gerekce": "Geçiş dönemi", "bitis": "2026-01-01"},
        {"id": "I4", "arac": "gitleaks", "kural": "generic-api-key", "dosya": "tests/ornek_veri.py", "gerekce": "Belge örneği", "bitis": "2099-12-31"},
    ]


class _Vekil(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True


class DevSecOpsLab:
    def __init__(self):
        self.temizlendi = False
        self.dis_istek = []
        self._tmp = self._vekil = self._th = None

    def __enter__(self):
        eksik = [a for a, p in ARAC.items() if not p.exists()]
        if eksik:
            raise RuntimeError("Araç bulunamadı (.deps): " + ", ".join(eksik) + ". İndirme yapılmaz; kurulum onayı gerekir.")
        self._tmp = tempfile.TemporaryDirectory(prefix="pu23_devsecops_")
        kok = Path(self._tmp.name)
        self.depo, self.ev = kok / "depo", kok / "ev"
        (self.depo / "uygulama").mkdir(parents=True)
        (self.depo / "tests").mkdir()
        self.ev.mkdir()
        kayit = self.dis_istek

        class H(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(3)
                try:
                    kayit.append(self.request.recv(2048).split(b"\r\n", 1)[0].decode("latin1")[:200])
                except Exception:
                    kayit.append("?")
                try:
                    self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                except Exception:
                    pass

        self._vekil = _Vekil(("127.0.0.1", 0), H)
        self._th = threading.Thread(target=self._vekil.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._th.start()
        px = "http://127.0.0.1:%d" % self._vekil.server_address[1]
        ev = str(self.ev)
        self.env = dict(os.environ, HTTP_PROXY=px, HTTPS_PROXY=px, ALL_PROXY=px, http_proxy=px, https_proxy=px, all_proxy=px,
                        NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost", USERPROFILE=ev, HOME=ev,
                        APPDATA=ev, LOCALAPPDATA=ev, XDG_CONFIG_HOME=ev, XDG_CACHE_HOME=ev, TRIVY_CACHE_DIR=str(self.ev / "trivy"),
                        SEMGREP_SEND_METRICS="off", SEMGREP_ENABLE_VERSION_CHECK="0", GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=str(self.ev / "gitconfig"), GIT_TERMINAL_PROMPT="0")
        return self

    def _git(self, *a):
        subprocess.run(["git", "-c", "user.name=pafta-lab", "-c", "user.email=lab@pafta.invalid", "-c", "commit.gpgsign=false",
                        "-c", "core.autocrlf=false", *a], cwd=self.depo, env=self.env, check=True, capture_output=True, timeout=20)

    def depo_kur(self):
        az = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        self.sirlar = {
            "aws_id": "AKIA" + "".join(secrets.choice(az) for _ in range(16)),
            "aws_gizli": "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40)),
            "gh": "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36)),
        }
        (self.depo / "uygulama/app.py").write_text(APP, encoding="utf-8")
        (self.depo / "uygulama/ayar.py").write_text('DB_YOLU = "veri.db"\nAWS_ACCESS_KEY_ID = "%s"\nAWS_SECRET_ACCESS_KEY = "%s"\nDEBUG = False\n'
                                                    % (self.sirlar["aws_id"], self.sirlar["aws_gizli"]), encoding="utf-8")
        (self.depo / "tests/ornek_veri.py").write_text(ORNEK, encoding="utf-8")
        (self.depo / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
        (self.depo / ".env").write_text("GITHUB_TOKEN=%s\n" % self.sirlar["gh"], encoding="utf-8")
        (self.depo / ".semgrep.yml").write_text(KURALLAR, encoding="utf-8")
        self._git("init", "-q", "-b", "main")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "ilk surum")
        (self.depo / ".env").unlink()
        (self.depo / ".gitignore").write_text(".env\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", ".env kaldirildi")

    def taramalar(self):
        komut = {
            "semgrep": [str(ARAC["semgrep"]), "scan", "--experimental", "--metrics=off", "--disable-version-check", "--config", ".semgrep.yml",
                        "--json", "--quiet", "."],
            "gitleaks": [str(ARAC["gitleaks"]), "git", ".", "--no-banner", "--redact", "--report-format", "json", "--report-path", "-",
                         "--log-level", "error"],
            "trivy": [str(ARAC["trivy"]), "fs", "--scanners", "secret,misconfig", "--skip-db-update", "--skip-check-update",
                      "--skip-version-check", "--disable-telemetry", "--format", "json", "--quiet", "."],
        }
        sonuc = {}

        def kos(ad):
            t0 = time.time()
            try:
                p = subprocess.run(komut[ad], cwd=self.depo, env=self.env, capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=50)
                sonuc[ad] = {"kod": p.returncode, "sn": round(time.time() - t0, 1), "stdout": p.stdout, "stderr": p.stderr[-400:]}
            except Exception as e:
                sonuc[ad] = {"kod": None, "sn": round(time.time() - t0, 1), "stdout": "", "stderr": type(e).__name__}

        th = [threading.Thread(target=kos, args=(a,)) for a in komut]
        for t in th:
            t.start()
        for t in th:
            t.join()
        ham = {}
        for ad, s in sonuc.items():
            # gitleaks bulgu olunca 1 döner; diğerleri 0 beklenir
            if s["kod"] not in ((0, 1) if ad == "gitleaks" else (0,)):
                raise RuntimeError(f"{ad} hata verdi: kod={s['kod']} {s['stderr']}")
            ham[ad] = json.loads(s["stdout"])
        return ham, {a: {"kod": s["kod"], "sn": s["sn"]} for a, s in sonuc.items()}

    def surumler(self):
        out = {}
        for ad, arg in (("gitleaks", ["version"]), ("trivy", ["--version"])):
            p = subprocess.run([str(ARAC[ad])] + arg, env=self.env, capture_output=True, text=True, timeout=15)
            out[ad] = p.stdout.strip().splitlines()[0] if p.stdout.strip() else "?"
        dist = sorted((DEPS / "semgrep-venv/Lib/site-packages").glob("semgrep-*.dist-info"))
        out["semgrep"] = dist[0].name[len("semgrep-"):-len(".dist-info")] if dist else "?"
        return out

    def __exit__(self, *a):
        if self._vekil is not None:
            self._vekil.shutdown()
            self._th.join(timeout=3)
            self._vekil.server_close()
        if self._tmp is not None:
            try:
                self._tmp.cleanup()
            except OSError:
                shutil.rmtree(self._tmp.name, ignore_errors=True)
        self.temizlendi = (self._th is None or not self._th.is_alive()) and (self._tmp is None or not Path(self._tmp.name).exists())


def _sizinti(nesne, sirlar):
    metin = json.dumps(nesne, ensure_ascii=False)
    return [k for k, v in sirlar.items() if v in metin]


def calistir(normalize, olc, ci_kapisi, kabul=False):
    import platform
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu23-devsecops", "python": platform.python_version(), "cihaz": platform.platform()}
    lab = DevSecOpsLab()
    try:
        with lab:
            lab.depo_kur()
            rec["surum"] = lab.surumler()
            ham, rec["sure"] = lab.taramalar()
            rec["dis_istek"] = list(lab.dis_istek)
            bulgular, ref_bulgular = [], []
            for ad in ("semgrep", "gitleaks", "trivy"):
                b = normalize(ad, ham[ad])
                r = referans_normalize(ad, ham[ad])
                if b != r:
                    raise AssertionError(f"normalize({ad!r}) gerçek çıktıda referanstan farklı: {b[:3]} … beklenen {r[:3]} …")
                bulgular += b
                ref_bulgular += r
            rec["bulgular"] = bulgular
            gercek = gercek_liste()
            rec["gercek"] = gercek
            olcum = olc(bulgular, gercek, {a: list(t) for a, t in KAPSAM.items()})
            if olcum != referans_olc(ref_bulgular, gercek, {a: list(t) for a, t in KAPSAM.items()}):
                raise AssertionError("olc gerçek bulgularda referanstan farklı")
            rec["olcum"] = olcum
            bugun = date.today().isoformat()
            ist = istisna_liste()
            ci = ci_kapisi(bulgular, ist, bugun)
            if ci != referans_ci(ref_bulgular, ist, bugun):
                raise AssertionError("ci_kapisi gerçek bulgularda referanstan farklı")
            rec["bugun"], rec["istisnalar"], rec["ci"] = bugun, ist, ci
            rec["sizinti"] = _sizinti({k: v for k, v in rec.items()}, lab.sirlar)
            # araç davranışı beklentileri (sabit sürümler); tutmazsa lab bozuk sayılır
            if (olcum["semgrep"]["kacan"], olcum["gitleaks"]["kacan"], olcum["trivy"]["kacan"]) != (["S4"], [], ["G3"]):
                raise AssertionError("Araç davranışı beklenenden farklı (sürüm ya da lab değişmiş olabilir)")
            if ci["gecti"] or rec["dis_istek"] or rec["sizinti"]:
                raise AssertionError("CI kapısı geçti ya da dış istek / sır sızıntısı var")
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
        out = d / ("pu23-" + str(time.time_ns()) + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("GERÇEK TARAMA (Semgrep · gitleaks · Trivy) · " + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print("süre:", json.dumps(rec["sure"]), "· dış istek:", len(rec["dis_istek"]))
    for a in ("semgrep", "gitleaks", "trivy", "hat"):
        print(a, json.dumps(rec["olcum"][a], ensure_ascii=False))
    print("CI:", "GEÇTİ" if rec["ci"]["gecti"] else "ENGELLENDİ", "· engelleyen", len(rec["ci"]["engelleyen"]),
          "· bastırılan", rec["ci"]["bastirilan"], "· süresi dolan", rec["ci"]["suresi_dolan"], "· kullanılmayan", rec["ci"]["kullanilmayan"])
    return rec
