# -*- coding: utf-8 -*-
"""Pafta · API tezgahı: oturumlu bir JSON API ve birkaç HTML sayfası.

Dersin hazırlık (`setup`) bloğu bu dosyayı düzenek sürecinde çalıştırır; dosya
127.0.0.1'in boş bir portunda "Pafta Bilet Masası API" uygulamasını başlatır.

Python derslerinde `api` modülü kurulur:

    import api
    api.SUNUCU          # "http://127.0.0.1:PORT"
    api.HOST, api.PORT

Kabuk derslerinde (PowerShell, Bash) hazırlık bloğu adresi çalışma klasöründeki
bir dosyaya yazar; betik onu okur.

Uygulama belirlenimlidir: veri her çalıştırmada sıfırdan kurulur, `Date` başlığı
sabittir (Mon, 19 Oct 2026 09:00:00 GMT), oturum çerezi sabit bir değerdir.

Uçlar
-----
POST /giris                 JSON {"kullanici", "parola"} · doğruysa 200 ve
                            `oturum` çerezi, yanlışsa 401 {"hata": "kimlik"}
POST /giris-form            form gövdesi (application/x-www-form-urlencoded)
                            {"kullanici", "parola"}; başka içerik türü 415
                            {"hata": "tur"}; kimlik /giris ile aynı, ayrıca
                            FORM_KULLANICI / FORM_PAROLA (özel karakterli) kabul edilir
GET  /api/biletler?sayfa=N  oturum ister; 401 {"hata": "oturum"}
                            200 {"sayfa", "toplam", "sonraki", "kayitlar": [...]}
                            sayfa 1'den başlar, sayfa başına 3 kayıt;
                            aralık dışı sayfa boş `kayitlar` verir
GET  /api/bilet/<id>        oturum ister; yoksa 404 {"hata": "yok"}
POST /api/bilet             oturum ister; JSON {"baslik", "oncelik"}
                            eksik/boş alan 400 {"hata": "alan"}
                            tanınmayan öncelik 400 {"hata": "oncelik"}
                            aynı başlık zaten varsa 409 {"hata": "yinelenen"}
                            doğruysa 201, Location başlığı ve kaydın kendisi
GET  /durum/<kod>           istenen HTTP durum kodunu döndürür (400-599)
GET  /yavas?ms=N&no=K       N milisaniye bekler (0-2000), {"no": K, "ms": N} döndürür;
                            aynı anda kaç isteğin beklediğini sayar
GET  /eszamanli             {"en_cok": M}: /yavas'ta aynı anda bekleyen en çok istek;
                            okununca sıfırlanır
GET  /bos                   204 No Content: gövdesiz yanıt
GET  /sayfa/biletler        tablo, bağlantılar ve gizli alanlı form içeren HTML
GET  /sayfa/bozuk           kapanmamış etiketleri olan bozuk HTML

İsteğe bağlı iki ek hizmet (yalnız çağıran derste başlar):

api.vekil_kur()     kimlik isteyen HTTP vekili (proxy) başlatır: api.VEKIL adresi,
                    api.VEKIL_KULLANICI / api.VEKIL_PAROLA. Kimliksiz ya da yanlış
                    kimlikli istek 407; geçen yanıta `Via: 1.1 pafta-vekil` eklenir.
                    Yalnız 127.0.0.1 hedeflerine iletir. api.vekil_sayac() geçen
                    istek sayısını verir.
api.tls_kur()       aynı uygulamayı HTTPS'te başlatır: api.HTTPS_SUNUCU
                    ("https://127.0.0.1:PORT"), ders CA'sı api.CA (PEM dosyası).
                    Sertifika yalnız 127.0.0.1 IP adına verilmiştir; `localhost`
                    adıyla bağlanmak ad uyuşmazlığıdır. CA sistem güven deposuna
                    eklenmez; geçici klasörde durur.
"""
import json
import os
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TARIH = "Mon, 19 Oct 2026 09:00:00 GMT"
OTURUM = "pafta-oturum-2026"
KULLANICI, PAROLA = "analist", "pafta123"
FORM_KULLANICI, FORM_PAROLA = "nöbetçi analist", "a&b=c d+%"     # elle kodlanırsa bozulur
VEKIL_KULLANICI, VEKIL_PAROLA = "vekil", "pafta-vekil-2026"
SAYFA_BOYU = 3
ONCELIKLER = ("düşük", "orta", "yüksek")

ESZAMANLI = {"simdi": 0, "en_cok": 0, "kilit": threading.Lock()}

BILETLER = [
    {"id": 101, "baslik": "web01 disk doldu", "oncelik": "yüksek", "durum": "açık", "sunucu": "web01"},
    {"id": 102, "baslik": "db01 yedek gecikti", "oncelik": "orta", "durum": "açık", "sunucu": "db01"},
    {"id": 103, "baslik": "cache01 yeniden başladı", "oncelik": "düşük", "durum": "çözüldü", "sunucu": "cache01"},
    {"id": 104, "baslik": "web02 sertifika süresi", "oncelik": "yüksek", "durum": "açık", "sunucu": "web02"},
    {"id": 105, "baslik": "db01 yavaş sorgu", "oncelik": "orta", "durum": "çözüldü", "sunucu": "db01"},
    {"id": 106, "baslik": "web03 5xx artışı", "oncelik": "yüksek", "durum": "açık", "sunucu": "web03"},
    {"id": 107, "baslik": "yedek01 disk testi", "oncelik": "düşük", "durum": "açık", "sunucu": "yedek01"},
]

SAYFA_HTML = """<!doctype html>
<html lang="tr">
<head><meta charset="utf-8"><title>Bilet Masası</title></head>
<body>
<h1 id="baslik">Açık Biletler</h1>
<p class="ozet">Toplam <span id="adet">{adet}</span> kayıt listeleniyor.</p>
<table id="biletler">
<thead><tr><th>No</th><th>Başlık</th><th>Öncelik</th><th>Sunucu</th></tr></thead>
<tbody>
{satirlar}
</tbody>
</table>
<ul class="baglantilar">
{baglantilar}
</ul>
<form id="yeni" method="post" action="/api/bilet">
<input type="hidden" name="belirtec" value="form-2026-abc">
<input type="text" name="baslik" value="">
<select name="oncelik"><option value="düşük">düşük</option><option value="orta" selected>orta</option><option value="yüksek">yüksek</option></select>
<button type="submit">Kaydet</button>
</form>
<footer><p class="not">Pafta eğitim verisi</p></footer>
</body>
</html>
"""

BOZUK_HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Bozuk Sayfa</title>
<body>
<h1 id="baslik">Yarım Liste
<ul class="kayitlar">
<li class="kayit">web01 <span class="deger">72
<li class="kayit">db01 <span class="deger">91</span>
<li class="kayit">cache01
</ul>
<p class="not">kapanmamış etiketler bilerek bırakıldı
</body>
"""


def _sayfa_html():
    acik = [b for b in BILETLER if b["durum"] == "açık"]
    satirlar = "\n".join(
        '<tr class="bilet" data-id="{id}"><td>{id}</td>'
        '<td><a href="/sayfa/bilet/{id}">{baslik}</a></td>'
        '<td class="oncelik">{oncelik}</td><td>{sunucu}</td></tr>'.format(**b) for b in acik)
    baglantilar = "\n".join(
        '<li><a class="ayrinti" href="/api/bilet/{id}">bilet {id}</a></li>'.format(**b) for b in acik[:3])
    return SAYFA_HTML.format(adet=len(acik), satirlar=satirlar, baglantilar=baglantilar)


class Isleyici(BaseHTTPRequestHandler):
    server_version = "PaftaApi/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def date_time_string(self, timestamp=None):
        return TARIH          # send_response'un kendi Date başlığı da sabit olsun

    # ── yardımcılar ──
    def _yolla(self, kod, govde, ctype="application/json; charset=utf-8", ek=()):
        if isinstance(govde, (dict, list)):
            govde = json.dumps(govde, ensure_ascii=False)
        if isinstance(govde, str):
            govde = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(govde)))
        for ad, deger in ek:
            self.send_header(ad, deger)
        self.end_headers()
        self.wfile.write(govde)

    def _oturum_var(self):
        cerez = self.headers.get("Cookie") or ""
        return f"oturum={OTURUM}" in cerez.replace("; ", ";").replace(";", "; ")

    def _govde_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 100_000:
            return None
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _durum_ucu(self, yol):
        try:
            kod = int(yol.rsplit("/", 1)[1])
        except ValueError:
            return self._yolla(400, {"hata": "kod"})
        if not 400 <= kod <= 599:
            return self._yolla(400, {"hata": "kod"})
        return self._yolla(kod, {"hata": "istek", "kod": kod})

    def _yavas(self, sorgu):
        try:
            ms = int((sorgu.get("ms") or ["0"])[0])
            no = int((sorgu.get("no") or ["0"])[0])
        except ValueError:
            return self._yolla(400, {"hata": "sayi"})
        if not 0 <= ms <= 2000:
            return self._yolla(400, {"hata": "ms"})
        with ESZAMANLI["kilit"]:
            ESZAMANLI["simdi"] += 1
            ESZAMANLI["en_cok"] = max(ESZAMANLI["en_cok"], ESZAMANLI["simdi"])
        try:
            time.sleep(ms / 1000)
        finally:
            with ESZAMANLI["kilit"]:
                ESZAMANLI["simdi"] -= 1
        return self._yolla(200, {"no": no, "ms": ms})

    # ── GET ──
    def do_GET(self):
        u = urlparse(self.path)
        yol = u.path
        if yol == "/sayfa/biletler":
            return self._yolla(200, _sayfa_html(), "text/html; charset=utf-8")
        if yol == "/sayfa/bozuk":
            return self._yolla(200, BOZUK_HTML, "text/html; charset=utf-8")
        if yol.startswith("/durum/"):
            return self._durum_ucu(yol)
        if yol == "/yavas":
            return self._yavas(parse_qs(u.query))
        if yol == "/bos":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if yol == "/eszamanli":
            with ESZAMANLI["kilit"]:
                en_cok, ESZAMANLI["en_cok"] = ESZAMANLI["en_cok"], 0
            return self._yolla(200, {"en_cok": en_cok})
        if yol == "/api/biletler":
            if not self._oturum_var():
                return self._yolla(401, {"hata": "oturum"})
            try:
                sayfa = int((parse_qs(u.query).get("sayfa") or ["1"])[0])
            except ValueError:
                return self._yolla(400, {"hata": "sayfa"})
            if sayfa < 1:
                return self._yolla(400, {"hata": "sayfa"})
            bas = (sayfa - 1) * SAYFA_BOYU
            dilim = BILETLER[bas:bas + SAYFA_BOYU]
            sonraki = sayfa + 1 if bas + SAYFA_BOYU < len(BILETLER) else None
            return self._yolla(200, {"sayfa": sayfa, "toplam": len(BILETLER),
                                     "sonraki": sonraki, "kayitlar": dilim})
        if yol.startswith("/api/bilet/"):
            if not self._oturum_var():
                return self._yolla(401, {"hata": "oturum"})
            try:
                no = int(yol.rsplit("/", 1)[1])
            except ValueError:
                return self._yolla(404, {"hata": "yok"})
            kayit = next((b for b in BILETLER if b["id"] == no), None)
            return self._yolla(200, kayit) if kayit else self._yolla(404, {"hata": "yok"})
        return self._yolla(404, {"hata": "yok"})

    # ── POST ──
    def do_POST(self):
        yol = urlparse(self.path).path
        if yol == "/giris":
            veri = self._govde_json() or {}
            if veri.get("kullanici") == KULLANICI and veri.get("parola") == PAROLA:
                cerez = f"oturum={OTURUM}; Path=/; HttpOnly"
                return self._yolla(200, {"durum": "açık", "kullanici": KULLANICI},
                                   ek=[("Set-Cookie", cerez)])
            return self._yolla(401, {"hata": "kimlik"})
        if yol == "/giris-form":
            n = int(self.headers.get("Content-Length") or 0)
            ham = self.rfile.read(n) if 0 < n <= 100_000 else b""
            tur = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if tur != "application/x-www-form-urlencoded":
                return self._yolla(415, {"hata": "tur"})
            alan = parse_qs(ham.decode("utf-8", "replace"))
            ikili = ((alan.get("kullanici") or [""])[0], (alan.get("parola") or [""])[0])
            if ikili in ((KULLANICI, PAROLA), (FORM_KULLANICI, FORM_PAROLA)):
                cerez = f"oturum={OTURUM}; Path=/; HttpOnly"
                return self._yolla(200, {"durum": "açık", "kullanici": ikili[0]},
                                   ek=[("Set-Cookie", cerez)])
            return self._yolla(401, {"hata": "kimlik"})
        if yol == "/api/bilet":
            if not self._oturum_var():
                return self._yolla(401, {"hata": "oturum"})
            veri = self._govde_json()
            if not isinstance(veri, dict):
                return self._yolla(400, {"hata": "govde"})
            baslik = (veri.get("baslik") or "").strip()
            oncelik = (veri.get("oncelik") or "").strip()
            if not baslik or not oncelik:
                return self._yolla(400, {"hata": "alan"})
            if oncelik not in ONCELIKLER:
                return self._yolla(400, {"hata": "oncelik"})
            eski = next((b for b in BILETLER if b["baslik"].casefold() == baslik.casefold()), None)
            if eski is not None:
                return self._yolla(409, {"hata": "yinelenen", "id": eski["id"]},
                                   ek=[("Location", f"/api/bilet/{eski['id']}")])
            no = max(b["id"] for b in BILETLER) + 1
            kayit = {"id": no, "baslik": baslik, "oncelik": oncelik, "durum": "açık", "sunucu": "-"}
            BILETLER.append(kayit)
            return self._yolla(201, kayit, ek=[("Location", f"/api/bilet/{no}")])
        return self._yolla(404, {"hata": "yok"})


TEK_ATLAMA = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
              "transfer-encoding", "upgrade"}
VEKIL_SAYAC = {"n": 0, "kilit": threading.Lock()}


class VekilIsleyici(BaseHTTPRequestHandler):
    """Kimlik isteyen, yalnız 127.0.0.1'e ileten küçük bir HTTP vekili."""
    server_version = "PaftaVekil/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def date_time_string(self, timestamp=None):
        return TARIH

    def _cevap(self, kod, govde, ek=()):
        govde = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        for ad, deger in ek:
            self.send_header(ad, deger)
        self.end_headers()
        self.wfile.write(govde)

    def _ilet(self):
        import base64
        import http.client
        beklenen = "Basic " + base64.b64encode(f"{VEKIL_KULLANICI}:{VEKIL_PAROLA}".encode()).decode()
        n = int(self.headers.get("Content-Length") or 0)
        govde = self.rfile.read(n) if n > 0 else None    # reddedilse de oku: kalan bayt sonraki isteğe karışmasın
        if self.headers.get("Proxy-Authorization") != beklenen:
            return self._cevap(407, {"hata": "vekil-kimlik"},
                               ek=[("Proxy-Authenticate", 'Basic realm="pafta-vekil"')])
        hedef = urlparse(self.path)
        if hedef.scheme != "http" or hedef.hostname != "127.0.0.1":
            return self._cevap(403, {"hata": "vekil-hedef"})
        basliklar = {k: v for k, v in self.headers.items() if k.lower() not in TEK_ATLAMA}
        baglanti = http.client.HTTPConnection(hedef.hostname, hedef.port or 80, timeout=10)
        try:
            baglanti.request(self.command, hedef.path + (("?" + hedef.query) if hedef.query else ""),
                             body=govde, headers=basliklar)
            yanit = baglanti.getresponse()
            veri = yanit.read()
        finally:
            baglanti.close()
        with VEKIL_SAYAC["kilit"]:
            VEKIL_SAYAC["n"] += 1
        self.send_response(yanit.status)
        for k, v in yanit.getheaders():
            if k.lower() not in TEK_ATLAMA and k.lower() not in ("content-length", "date", "server"):
                self.send_header(k, v)
        self.send_header("Via", "1.1 pafta-vekil")
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    do_GET = do_POST = _ilet

    def do_CONNECT(self):
        self._cevap(405, {"hata": "connect"})


def _arka_planda(sunucu):
    sunucu.daemon_threads = True
    sunucu.handle_error = lambda istek, adres: None     # iş parçacığı hataları öğrenci çıktısına karışmasın
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu.server_address[:2]


def vekil_kur():
    m = sys.modules["api"]
    if getattr(m, "VEKIL", None):
        return m.VEKIL
    host, port = _arka_planda(ThreadingHTTPServer(("127.0.0.1", 0), VekilIsleyici))
    m.VEKIL = f"http://{host}:{port}"
    m.VEKIL_KULLANICI, m.VEKIL_PAROLA = VEKIL_KULLANICI, VEKIL_PAROLA
    m.vekil_sayac = lambda: VEKIL_SAYAC["n"]
    return m.VEKIL


def tls_kur():
    """Ders CA'sı ve 127.0.0.1 için sertifika üretip uygulamayı HTTPS'te de açar."""
    m = sys.modules["api"]
    if getattr(m, "HTTPS_SUNUCU", None):
        return m.HTTPS_SUNUCU
    import atexit
    import datetime
    import ipaddress
    import shutil
    import ssl
    import tempfile
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    simdi = datetime.datetime.now(datetime.timezone.utc)
    ca_anahtar = ec.generate_private_key(ec.SECP256R1())
    ca_ad = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Pafta ders CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_ad).issuer_name(ca_ad).public_key(ca_anahtar.public_key())
          .serial_number(x509.random_serial_number())
          .not_valid_before(simdi - datetime.timedelta(minutes=5)).not_valid_after(simdi + datetime.timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_anahtar.public_key()), critical=False)
          .sign(ca_anahtar, hashes.SHA256()))
    anahtar = ec.generate_private_key(ec.SECP256R1())
    sertifika = (x509.CertificateBuilder()
                 .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
                 .issuer_name(ca_ad).public_key(anahtar.public_key()).serial_number(x509.random_serial_number())
                 .not_valid_before(simdi - datetime.timedelta(minutes=5))
                 .not_valid_after(simdi + datetime.timedelta(days=1))
                 .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                 .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                                critical=False)
                 .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                 .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_anahtar.public_key()),
                                critical=False)
                 .sign(ca_anahtar, hashes.SHA256()))
    klasor = tempfile.mkdtemp(prefix="pafta_api_tls_")
    atexit.register(shutil.rmtree, klasor, True)
    ca_yolu = os.path.join(klasor, "pafta-ders-ca.pem")
    with open(ca_yolu, "wb") as f:
        f.write(ca.public_bytes(serialization.Encoding.PEM))
    with open(os.path.join(klasor, "sunucu.pem"), "wb") as f:
        f.write(sertifika.public_bytes(serialization.Encoding.PEM))
    with open(os.path.join(klasor, "sunucu.key"), "wb") as f:
        f.write(anahtar.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()))
    baglam = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    baglam.load_cert_chain(os.path.join(klasor, "sunucu.pem"), os.path.join(klasor, "sunucu.key"))
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    sunucu.socket = baglam.wrap_socket(sunucu.socket, server_side=True)
    host, port = _arka_planda(sunucu)
    m.HTTPS_SUNUCU, m.HTTPS_PORT, m.CA = f"https://{host}:{port}", port, ca_yolu
    return m.HTTPS_SUNUCU


def _kur():
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    host, port = _arka_planda(sunucu)

    m = types.ModuleType("api")
    m.__doc__ = __doc__
    m.HOST, m.PORT, m.SUNUCU = host, port, f"http://{host}:{port}"
    m.KULLANICI, m.PAROLA = KULLANICI, PAROLA
    m.FORM_KULLANICI, m.FORM_PAROLA = FORM_KULLANICI, FORM_PAROLA
    m.SUNUCU_NESNESI = sunucu
    m.vekil_kur, m.tls_kur = vekil_kur, tls_kur
    sys.modules["api"] = m
    return m


_kur()
