"""pu24: keşif tezgâhı. Kendi 127.0.0.1 "Pafta Market" sunucusu (yumuşak 404 döner, ters vekil gibi
X-Forwarded-For'u kaydeder). .deps altındaki sabit sürümlü ffuf ve nuclei yalnız bu sunucuya koşar; nuclei yalnız
öğrencinin ürettiği şablonlarla, güncelleme denetimi kapalı çalışır. Erişim kaydı öğrencinin tespit işlevine verilir.
Araçlar, her isteği kaydedip reddeden yerel bir vekil üzerinden koşar. Sentetik veri; yalnız kendi kaynaklarını temizler."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import http.client
import json
import os
import re
import secrets
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks/purple/fixtures/pu24_kesif"
DEPS = ROOT / ".deps"
FFUF = DEPS / "ffuf-2.3.0/acik/ffuf.exe"
NUCLEI = DEPS / "nuclei-3.11.1/acik/nuclei.exe"
ONEM = ("info", "low", "medium", "high", "critical")
YUMUSAK = "Sayfa bulunamadi"


def hazirla(hedef=None):
    dest = Path(hedef or Path.cwd()) / "kesif"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("ornekler.json", "kelimeler.txt", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


# ---------------------------------------------------------------- referanslar
def referans_ffuf(ham, taban):
    try:
        if not isinstance(ham["results"], list):
            raise ValueError("tür")
        imza = (taban["status"], taban["words"], taban["lines"])
        if any(not isinstance(x, int) for x in imza):
            raise ValueError("taban")
        out = []
        for r in ham["results"]:
            kelime = r["input"]["FUZZ"]
            if not kelime.strip("/") or not all(isinstance(r[k], int) for k in ("status", "words", "lines", "length")):
                raise ValueError("sonuç")
            if r["status"] == 404 or (r["status"], r["words"], r["lines"]) == imza:
                continue
            out.append({"yol": "/" + kelime.lstrip("/"), "durum": r["status"], "uzunluk": r["length"],
                        "yonlendirme": r.get("redirectlocation") or None})
    except (KeyError, TypeError, AttributeError):
        raise ValueError("bozuk ffuf çıktısı")
    return sorted(out, key=lambda x: x["yol"])


def referans_sablon(kimlik, yol, kelimeler, onem, haric=()):
    if not isinstance(kimlik, str) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", kimlik):
        raise ValueError("kimlik")
    if not isinstance(yol, str) or not yol.startswith("/") or "{{" in yol or any(c.isspace() for c in yol):
        raise ValueError("yol")
    for liste in (kelimeler, haric):
        if not isinstance(liste, (list, tuple)) or any(not isinstance(k, str) or not k for k in liste):
            raise ValueError("kelime listesi")
    if not kelimeler or onem not in ONEM:
        raise ValueError("kelime ya da önem")
    eslestir = [{"type": "status", "status": [200]},
                {"type": "word", "part": "body", "words": list(kelimeler), "condition": "and"}]
    if haric:
        eslestir.append({"type": "word", "part": "body", "words": list(haric), "negative": True})
    return {"id": kimlik, "info": {"name": kimlik, "author": "pafta-ogrenci", "severity": onem},
            "http": [{"method": "GET", "path": ["{{BaseURL}}" + yol], "matchers-condition": "and", "matchers": eslestir}]}


def referans_tespit(kayitlar, esik, pencere, guvenilir):
    if (not isinstance(kayitlar, list) or not isinstance(esik, int) or esik < 1 or not isinstance(pencere, (int, float))
            or pencere <= 0 or not isinstance(guvenilir, (list, tuple, set))):
        raise ValueError("parametre")
    olay = {}
    try:
        for k in kayitlar:
            if not isinstance(k["t"], (int, float)) or not isinstance(k["kaynak"], str) or not isinstance(k["bulunamadi"], bool):
                raise ValueError("kayıt")
            xff = k.get("xff")
            istemci = xff.split(",")[-1].strip() if k["kaynak"] in guvenilir and isinstance(xff, str) and xff.strip() else k["kaynak"]
            o = olay.setdefault(istemci, {"t": [], "yol": set(), "ua": set()})
            o["ua"].add(k.get("ua") or "-")
            if k["bulunamadi"]:
                o["t"].append(k["t"])
                o["yol"].add(k["yol"])
    except (KeyError, TypeError, AttributeError):
        raise ValueError("bozuk kayıt")
    alarm = []
    for istemci, o in olay.items():
        t = sorted(o["t"])
        en, j = 0, 0
        for i in range(len(t)):
            while t[i] - t[j] > pencere:
                j += 1
            en = max(en, i - j + 1)
        if en >= esik:
            alarm.append({"istemci": istemci, "en_cok": en, "farkli_yol": len(o["yol"]), "ilk": t[0], "son": t[-1], "ua": sorted(o["ua"])})
    return sorted(alarm, key=lambda a: a["istemci"])


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json", "re") for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                                                  or n.module == "purple_kesif_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) for x in n.targets):
            return False
    return True


# ---------------------------------------------------------------- lab
SAYFA = {"/": (200, "<html><h1>Pafta Market</h1><a href=\"/urunler\">Ürünler</a></html>"),
         "/urunler": (200, "<html><ul><li>kalem</li><li>defter</li></ul></html>"),
         "/admin": (302, ""),
         "/yedek": (200, "<html>yedek-2026-10.zip indir</html>"),
         "/api/surum": (200, '{"urun":"pafta-market","surum":"1.4.2"}'),
         "/.git/HEAD": (200, "ref: refs/heads/main\n")}
TARAYICI_XFF, KULLANICI_XFF = "10.66.0.9", "10.20.0.5"


class _Vekil(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True


class KesifLab:
    def __init__(self):
        self.kayit, self.dis_istek = [], []
        self._kilit = threading.Lock()
        self.temizlendi = False
        self._tmp = self._srv = self._th = self._vekil = self._vth = None

    def __enter__(self):
        eksik = [p.name for p in (FFUF, NUCLEI) if not p.exists()]
        if eksik:
            raise RuntimeError("Araç bulunamadı (.deps): " + ", ".join(eksik) + ". İndirme yapılmaz; kurulum onayı gerekir.")
        self._tmp = tempfile.TemporaryDirectory(prefix="pu24_kesif_")
        self.is_ = Path(self._tmp.name)
        (self.is_ / "ev").mkdir()
        lab = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                yol = self.path.split("?", 1)[0]
                st, g = SAYFA.get(yol, (200, f"<html>{YUMUSAK}: {yol[:80]}</html>"))
                with lab._kilit:
                    lab.kayit.append({"t": round(time.time(), 4), "kaynak": self.client_address[0], "xff": self.headers.get("X-Forwarded-For"),
                                      "yol": yol[:120], "durum": st, "bulunamadi": yol not in SAYFA, "ua": (self.headers.get("User-Agent") or "")[:120]})
                b = g.encode("utf-8")
                self.send_response(st)
                if st == 302:
                    self.send_header("Location", "/giris")
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

        self._srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self._srv.server_address[1]
        self._th = threading.Thread(target=self._srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self._th.start()
        dis = self.dis_istek

        class V(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(3)
                try:
                    dis.append(self.request.recv(2048).split(b"\r\n", 1)[0].decode("latin1")[:200])
                except Exception:
                    dis.append("?")
                try:
                    self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                except Exception:
                    pass

        self._vekil = _Vekil(("127.0.0.1", 0), V)
        self._vth = threading.Thread(target=self._vekil.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._vth.start()
        px, ev = "http://127.0.0.1:%d" % self._vekil.server_address[1], str(self.is_ / "ev")
        self.env = dict(os.environ, HTTP_PROXY=px, HTTPS_PROXY=px, ALL_PROXY=px, http_proxy=px, https_proxy=px, all_proxy=px,
                        NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost", USERPROFILE=ev, HOME=ev, APPDATA=ev,
                        LOCALAPPDATA=ev, XDG_CONFIG_HOME=ev, XDG_CACHE_HOME=ev)
        return self

    def get(self, yol, xff, ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) PaftaKullanici/1.0"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            c.request("GET", yol, headers={"X-Forwarded-For": xff, "User-Agent": ua})
            r = c.getresponse()
            govde = r.read().decode("utf-8")
            return {"status": r.status, "words": len(govde.split()), "lines": govde.count("\n") + 1}
        finally:
            c.close()

    def ffuf(self, kelimeler):
        (self.is_ / "kelimeler.txt").write_text("\n".join(kelimeler) + "\n", encoding="utf-8")
        p = subprocess.run([str(FFUF), "-u", f"http://127.0.0.1:{self.port}/FUZZ", "-w", "kelimeler.txt", "-mc", "all", "-t", "5",
                            "-of", "json", "-o", "ffuf.json", "-s", "-H", "X-Forwarded-For: " + TARAYICI_XFF],
                           cwd=self.is_, env=self.env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        if p.returncode != 0:
            raise RuntimeError("ffuf hata verdi: " + p.stderr[-300:])
        return json.loads((self.is_ / "ffuf.json").read_text(encoding="utf-8"))

    def nuclei(self, sablonlar):
        arg = []
        for s in sablonlar:
            yol = self.is_ / (s["id"] + ".yaml")
            yol.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
            arg += ["-t", yol.name]
        p = subprocess.run([str(NUCLEI), "-duc", "-ni", "-nc", "-silent", "-jsonl", "-or", "-ot", "-u", f"http://127.0.0.1:{self.port}",
                            "-H", "X-Forwarded-For: " + TARAYICI_XFF] + arg,
                           cwd=self.is_, env=self.env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
        if p.returncode != 0:
            raise RuntimeError("nuclei hata verdi: " + p.stderr[-300:])
        out = []
        for satir in p.stdout.splitlines():
            if satir.strip().startswith("{"):
                j = json.loads(satir)
                out.append({"sablon": j.get("template-id"), "adres": j.get("matched-at")})
        return sorted(out, key=lambda x: (x["sablon"], x["adres"]))

    def __exit__(self, *a):
        for srv, th in ((self._srv, self._th), (self._vekil, self._vth)):
            if srv is not None:
                srv.shutdown()
                th.join(timeout=3)
                srv.server_close()
        if self._tmp is not None:
            try:
                self._tmp.cleanup()
            except OSError:
                shutil.rmtree(self._tmp.name, ignore_errors=True)
        self.temizlendi = all(th is None or not th.is_alive() for th in (self._th, self._vth)) and (self._tmp is None or not self.is_.exists())


SABLON_GIRDI = [("pafta-surum-ifsasi", "/api/surum", ["pafta-market", '"surum"'], "low", [YUMUSAK]),
                ("pafta-git-ifsasi", "/.git/HEAD", ["ref: refs/heads/"], "medium", [YUMUSAK]),
                ("pafta-yonetim-paneli", "/yonetim", ["yonetim"], "medium", [YUMUSAK])]


def calistir(ffuf_ayikla, sablon_kur, tarama_tespit, kabul=False):
    import platform
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu24-kesif", "python": platform.python_version(), "cihaz": platform.platform()}
    lab = KesifLab()
    kelimeler = [x.strip() for x in (FIXTURE / "kelimeler.txt").read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
    try:
        with lab:
            rec["address"], rec["port"] = "127.0.0.1", lab.port
            for yol in ("/", "/urunler", "/api/surum", "/urunler/kalm"):
                lab.get(yol, KULLANICI_XFF)
            taban = lab.get("/" + secrets.token_hex(8), TARAYICI_XFF, "pafta-kalibrasyon/1.0")
            rec["taban"] = taban
            t0 = time.time()
            ham = lab.ffuf(kelimeler)
            rec["ffuf_sn"] = round(time.time() - t0, 1)
            bul = ffuf_ayikla(ham, taban)
            if bul != referans_ffuf(ham, taban):
                raise AssertionError("ffuf_ayikla gerçek çıktıda referanstan farklı")
            rec["ffuf_ham_sonuc"], rec["ffuf_bulunan"] = len(ham["results"]), bul
            sab = [sablon_kur(*g) for g in SABLON_GIRDI]
            if sab != [referans_sablon(*g) for g in SABLON_GIRDI]:
                raise AssertionError("sablon_kur referanstan farklı şablon üretti")
            saf = referans_sablon("pafta-yonetim-saf", "/yonetim", ["yonetim"], "medium")
            t0 = time.time()
            rec["nuclei"] = lab.nuclei(sab + [saf])
            rec["nuclei_sn"] = round(time.time() - t0, 1)
            for yol in ("/urunler", "/"):
                lab.get(yol, KULLANICI_XFF)
            rec["kayit_sayisi"] = len(lab.kayit)
            alarm = tarama_tespit(list(lab.kayit), 5, 2.0, ["127.0.0.1"])
            if alarm != referans_tespit(list(lab.kayit), 5, 2.0, ["127.0.0.1"]):
                raise AssertionError("tarama_tespit gerçek kayıtta referanstan farklı")
            rec["alarm"] = alarm
            rec["guvenilmez_vekil_alarm"] = referans_tespit(list(lab.kayit), 5, 2.0, [])
            rec["dis_istek"] = list(lab.dis_istek)
            # beklentiler: araçlar ve lab doğru çalıştı mı
            yollar = {b["yol"] for b in bul}
            if yollar != {"/" + k for k in kelimeler if "/" + k in SAYFA}:
                raise AssertionError("ffuf + ayıklama gerçek yolları tam bulmadı: " + str(sorted(yollar)))
            esles = {(n["sablon"], n["adres"].rsplit(str(lab.port), 1)[-1]) for n in rec["nuclei"]}
            if esles != {("pafta-surum-ifsasi", "/api/surum"), ("pafta-git-ifsasi", "/.git/HEAD"), ("pafta-yonetim-saf", "/yonetim")}:
                raise AssertionError("nuclei eşleşmeleri beklenenden farklı: " + str(sorted(esles)))
            if [a["istemci"] for a in alarm] != [TARAYICI_XFF] or rec["dis_istek"]:
                raise AssertionError("tespit yalnız tarayıcıyı bulmalı; dış istek olmamalı")
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
        out = d / ("pu24-" + str(time.time_ns()) + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("GERÇEK KEŞİF (ffuf · nuclei · erişim kaydı) · " + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print("ffuf ham sonuç:", rec["ffuf_ham_sonuc"], "· gerçek yol:", [b["yol"] for b in rec["ffuf_bulunan"]])
    print("nuclei:", [(n["sablon"], n["adres"].rsplit(str(rec["port"]), 1)[-1]) for n in rec["nuclei"]])
    print("alarm:", json.dumps(rec["alarm"], ensure_ascii=False))
    print("güvenilir vekil listesi boşken alarm:", [a["istemci"] for a in rec["guvenilmez_vekil_alarm"]], "· dış istek:", len(rec["dis_istek"]))
    return rec
