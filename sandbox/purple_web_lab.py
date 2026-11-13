"""pu22: yerel web tezgâhı. stdlib HTTP sunucusunda açık/korumalı uç çiftleri: yansıyan XSS, str.format şablon enjeksiyonu, XXE. Korumalı uçlar öğrencinin işlevlerini kullanır. Sentetik veri; yalnız kendi kaynaklarını temizler."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import http.client
import io
import json
import secrets
import shutil
import string
import tempfile
import threading
import urllib.parse
import xml.parsers.expat
import xml.sax
import xml.sax.expatreader
import xml.sax.handler
import xml.sax.saxutils

FIXTURE = Path(__file__).resolve().parents[1] / "tracks/purple/fixtures/pu22_web"


def hazirla(hedef=None):
    dest = Path(hedef or Path.cwd()) / "web"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("ornekler.json", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


def referans_html(metin):
    if not isinstance(metin, str):
        raise ValueError("metin")
    return metin.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")


def referans_sablon(sablon, izinli):
    if not isinstance(sablon, str) or not isinstance(izinli, (list, tuple)) or any(not isinstance(a, str) for a in izinli):
        raise ValueError("tür")
    alanlar = set()
    for _, ad, bicim, donusum in string.Formatter().parse(sablon):
        if ad is None:
            continue
        if ad not in izinli or bicim or donusum:
            raise ValueError("izinsiz alan: " + repr(ad))
        alanlar.add(ad)
    return sorted(alanlar)


def referans_dtd(belge):
    if not isinstance(belge, bytes):
        raise ValueError("bayt")
    p = xml.parsers.expat.ParserCreate()
    bulundu = []
    p.StartDoctypeDeclHandler = lambda *a: bulundu.append("doctype")
    try:
        p.Parse(belge, True)
    except xml.parsers.expat.ExpatError as e:
        raise ValueError("bozuk XML: " + str(e))
    return bool(bulundu)


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json", "re", "string", "xml.parsers.expat") for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                                                  or n.module == "string" and all(a.name == "Formatter" for a in n.names)
                                                  or n.module == "purple_web_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) and not (x.attr.endswith("Handler") and isinstance(x.value, ast.Name)) for x in n.targets):
            return False
    return True


class _Kullanici:
    def __init__(self, ad, ayar):
        self.ad = ad
        self.ayar = ayar


class _Metin(xml.sax.ContentHandler):
    def __init__(self):
        super().__init__()
        self.metin = ""

    def characters(self, c):
        self.metin += c


def _sax(belge, dis_varlik):
    h = _Metin()
    p = xml.sax.make_parser()
    p.setContentHandler(h)
    p.setFeature(xml.sax.handler.feature_external_ges, dis_varlik)
    p.parse(io.BytesIO(belge))
    return h.metin.strip()


class YerelWebLab:
    def __init__(self, html_fn, sablon_fn, dtd_fn):
        self.html_fn, self.sablon_fn, self.dtd_fn = html_fn, sablon_fn, dtd_fn
        self.gizli_ayar = "PU22_AYAR_" + secrets.token_hex(6)
        self.gizli_dosya = "PU22_DOSYA_" + secrets.token_hex(6)
        self.denetim = []
        self._kilit = threading.Lock()
        self.temizlendi = False
        self._tmp = self._srv = self._th = None

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="pu22_web_")
        self.dosya = Path(self._tmp.name) / "gizli.txt"
        self.dosya.write_text(self.gizli_dosya, encoding="ascii")
        _sax(b"<isinma/>", True)
        lab = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _yanit(self, status, govde, tur="text/html; charset=utf-8"):
                raw = govde.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return govde

            def do_GET(self):
                u = urllib.parse.urlsplit(self.path)
                q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
                girdi = (q.get("q") or q.get("sablon") or [""])[0]
                try:
                    if u.path == "/vulnerable/ara":
                        st, g = 200, "<p>Sonuç: " + girdi + "</p>"
                    elif u.path == "/secure/ara":
                        st, g = 200, "<p>Sonuç: " + lab.html_fn(girdi) + "</p>"
                    elif u.path == "/vulnerable/selam":
                        st, g = 200, girdi.format(u=_Kullanici("Deniz", {"GIZLI": lab.gizli_ayar}), ad="Deniz")
                    elif u.path == "/secure/selam":
                        try:
                            lab.sablon_fn(girdi, ("ad",))
                            st, g = 200, girdi.format_map({"ad": "Deniz"})
                        except ValueError:
                            st, g = 400, "izinsiz sablon"
                    else:
                        st, g = 404, "yok"
                except Exception as e:
                    st, g = 500, "hata: " + type(e).__name__
                lab._kaydet(u.path, girdi, st, g)
                self._yanit(st, g)

            def do_POST(self):
                n = int(self.headers.get("Content-Length", "0"))
                belge = self.rfile.read(n) if 0 < n <= 8192 else b""
                try:
                    if self.path == "/vulnerable/xml":
                        st, g = 200, _sax(belge, True)
                    elif self.path == "/secure/xml":
                        try:
                            if lab.dtd_fn(belge):
                                st, g = 400, "DTD reddedildi"
                            else:
                                st, g = 200, _sax(belge, False)
                        except ValueError:
                            st, g = 400, "bozuk XML"
                    else:
                        st, g = 404, "yok"
                except Exception as e:
                    st, g = 500, "hata: " + type(e).__name__
                lab._kaydet(self.path, belge.decode("utf-8", "replace"), st, g)
                self._yanit(st, g, "text/plain; charset=utf-8")

        self._srv = HTTPServer(("127.0.0.1", 0), H)
        self.port = self._srv.server_address[1]
        self._th = threading.Thread(target=self._srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self._th.start()
        return self

    def _kaydet(self, route, girdi, st, govde):
        with self._kilit:
            self.denetim.append({"route": route, "girdi": girdi[:300], "status": st,
                                 "gizli_sizdi": self.gizli_ayar in govde or self.gizli_dosya in govde})

    def get(self, yol, **q):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            c.request("GET", yol + "?" + urllib.parse.urlencode(q))
            r = c.getresponse()
            return {"status": r.status, "govde": r.read().decode("utf-8")}
        finally:
            c.close()

    def post(self, yol, belge):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            c.request("POST", yol, belge, {"Content-Type": "application/xml"})
            r = c.getresponse()
            return {"status": r.status, "govde": r.read().decode("utf-8")}
        finally:
            c.close()

    def __exit__(self, *a):
        if self._srv is not None:
            self._srv.shutdown()
            self._th.join(timeout=3)
            self._srv.server_close()
        if self._tmp is not None:
            self._tmp.cleanup()
        self.temizlendi = (self._th is None or not self._th.is_alive()) and (self._tmp is None or not self.dosya.exists())


EK_HTML = ["", "düz metin", "a&b", "&lt;", "<a href=\"x\">'</a>", "Ayşe & Ali <3", "\"'\"", "&amp;amp;"]
EK_SABLON = [("Merhaba {ad}!", ("ad",)), ("{{ad}} {ad}", ("ad",)), ("{ad}{ad}{soyad}", ("ad", "soyad")), ("sabit", ("ad",)), ("{{{ad}}}", ("ad",)),
             ("{u.ayar[GIZLI]}", ("ad",)), ("{ad.__class__}", ("ad",)), ("{ad!r}", ("ad",)), ("{ad:>10}", ("ad",)), ("{}", ("ad",)), ("{0}", ("ad",)), ("{ad", ("ad",)), ("}", ("ad",))]


def calistir(guvenli_html, sablon_dogrula, dtd_var_mi, kabul=False):
    import os, platform, time
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu22-web", "python": platform.python_version(), "expat": xml.parsers.expat.EXPAT_VERSION, "cihaz": platform.platform()}
    lab = YerelWebLab(guvenli_html, sablon_dogrula, dtd_var_mi)
    try:
        with lab:
            rec["address"] = "127.0.0.1"
            rec["port"] = lab.port
            isaret = "PU22-" + secrets.token_hex(4)
            xss = f'<b id="{isaret}">x</b>'
            mesru_xml = "<siparis><urun>kalem &amp; defter</urun></siparis>".encode()
            xxe = f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "{lab.dosya.resolve().as_uri()}">]><r>&x;</r>'.encode()
            xxe16 = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE r [<!ENTITY x "y">]><r>&x;</r>'.encode("utf-16")
            denemeler = [
                ("xss-mesru-acik", "GET", "/vulnerable/ara", {"q": "Ayşe & Ali <3"}), ("xss-mesru-korumali", "GET", "/secure/ara", {"q": "Ayşe & Ali <3"}),
                ("xss-saldiri-acik", "GET", "/vulnerable/ara", {"q": xss}), ("xss-saldiri-korumali", "GET", "/secure/ara", {"q": xss}),
                ("sablon-mesru-acik", "GET", "/vulnerable/selam", {"sablon": "Merhaba {ad}!"}), ("sablon-mesru-korumali", "GET", "/secure/selam", {"sablon": "Merhaba {ad}!"}),
                ("sablon-saldiri-acik", "GET", "/vulnerable/selam", {"sablon": "{u.ayar[GIZLI]}"}), ("sablon-saldiri-korumali", "GET", "/secure/selam", {"sablon": "{u.ayar[GIZLI]}"}),
                ("xml-mesru-acik", "POST", "/vulnerable/xml", mesru_xml), ("xml-mesru-korumali", "POST", "/secure/xml", mesru_xml),
                ("xml-saldiri-acik", "POST", "/vulnerable/xml", xxe), ("xml-saldiri-korumali", "POST", "/secure/xml", xxe),
                ("xml-utf16-korumali", "POST", "/secure/xml", xxe16)]
            yan = {}
            for ad, yontem, yol, veri in denemeler:
                yan[ad] = lab.get(yol, **veri) if yontem == "GET" else lab.post(yol, veri)
            rec["yanitlar"] = yan
            rec["denetim"] = list(lab.denetim)
            rec["isaret"] = isaret
            beklenen = {"xss-mesru-korumali": (200, "<p>Sonuç: Ayşe &amp; Ali &lt;3</p>"), "sablon-mesru-acik": (200, "Merhaba Deniz!"),
                        "sablon-mesru-korumali": (200, "Merhaba Deniz!"), "xml-mesru-acik": (200, "kalem & defter"), "xml-mesru-korumali": (200, "kalem & defter")}
            for ad, (st, g) in beklenen.items():
                if (yan[ad]["status"], yan[ad]["govde"]) != (st, g):
                    raise AssertionError(f"Meşru istek bozuldu: {ad} → {yan[ad]}")
            if xss not in yan["xss-saldiri-acik"]["govde"] or lab.gizli_ayar not in yan["sablon-saldiri-acik"]["govde"] or lab.gizli_dosya not in yan["xml-saldiri-acik"]["govde"]:
                raise AssertionError("Açık uçlar beklenen gerçek açığı göstermedi (lab bozuk)")
            if xss in yan["xss-saldiri-korumali"]["govde"] or yan["sablon-saldiri-korumali"]["status"] != 400 or yan["xml-saldiri-korumali"]["status"] != 400 or yan["xml-utf16-korumali"]["status"] != 400:
                raise AssertionError("Korumalı uç saldırıyı durdurmadı")
            if any(d["gizli_sizdi"] for d in lab.denetim if d["route"].startswith("/secure/")):
                raise AssertionError("Korumalı uçtan gizli değer sızdı")
        rec["html"] = [guvenli_html(x) for x in EK_HTML]
        rec["html_referans"] = [referans_html(x) for x in EK_HTML]

        def dene(f, *a):
            try:
                return f(*a)
            except ValueError:
                return "ValueError"
        rec["sablon"] = [dene(sablon_dogrula, s, i) for s, i in EK_SABLON]
        rec["sablon_referans"] = [dene(referans_sablon, s, i) for s, i in EK_SABLON]
        belgeler = [mesru_xml, xxe, xxe16, b'<!DOCTYPE r SYSTEM "x.dtd"><r/>', b"<r>", b"<r/>"]
        rec["dtd"] = [dene(dtd_var_mi, b) for b in belgeler]
        rec["dtd_referans"] = [dene(referans_dtd, b) for b in belgeler]
        for ad in ("html", "sablon", "dtd"):
            if rec[ad] != rec[ad + "_referans"]:
                raise AssertionError(ad + " işlevi gerçek örneklerde referanstan farklı")
        rec["kabul"] = bool(kabul)
    except BaseException as e:
        rec["error"] = {"type": type(e).__name__, "msg": str(e)}
        raise
    finally:
        rec["cleanup"] = lab.temizlendi
        if not lab.temizlendi:
            rec["kabul"] = False
        root = Path(__file__).resolve().parents[1]
        d = Path(os.environ.get("PAFTA_DATA", str(root / "data"))) / "purple-kanit"
        d.mkdir(parents=True, exist_ok=True)
        out = d / ("pu22-" + str(time.time_ns()) + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("GERÇEK HTTP (XSS · şablon · XXE) · " + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print(json.dumps({ad: [y["status"], y["govde"][:80]] for ad, y in rec["yanitlar"].items()}, ensure_ascii=False))
    return rec
