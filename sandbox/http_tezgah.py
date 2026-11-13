# -*- coding: utf-8 -*-
"""Pafta · HTTP tezgahı: her çalıştırmada arka planda koşan nötr bir demo web uygulaması.

HttpRunner (engine/runners.py) bu dosyayı görevin hazırlığından önce düzenek sürecinde
çalıştırır. Dosya 127.0.0.1'in boş bir portunda "Pafta Bilet Masası" uygulamasını başlatır
ve kullanıcı kodu için `tezgah` modülünü kurar:

    import tezgah
    tezgah.SUNUCU            # "http://127.0.0.1:PORT" (urllib için)
    tezgah.HOST, tezgah.PORT
    tezgah.gonder(istek)     # ham isteği (str ya da bytes) sokete yazar, ham yanıtı metin döndürür
    tezgah.gonder_bayt(istek)
    tezgah.yanit(istek)      # gönderir ve ayrıştırır → Yanit: surum, durum, neden, basliklar,
                             #   baslik(ad), hepsi(ad), govde, govde_bayt, json(), ham

Yanıtlar belirlenimlidir: Date başlığı sabit (Mon, 19 Oct 2026 09:00:00 GMT), Server başlığı
"PaftaSunucu/1.0", oturum çerezi sabit bir değerdir. Uygulamanın durumu (biletler, istek
sayacı) her çalıştırmada sıfırdan kurulur.
"""
import base64
import email.utils
import gzip
import html
import json
import re
import socket
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

TARIH = "Mon, 19 Oct 2026 09:00:00 GMT"
SURUM = "2.4.1"
SUNUCULAR = [
    {"ad": "web01", "rol": "web", "sehir": "İstanbul", "cpu": 72},
    {"ad": "web02", "rol": "web", "sehir": "Ankara", "cpu": 45},
    {"ad": "db01", "rol": "db", "sehir": "İstanbul", "cpu": 91},
    {"ad": "cache01", "rol": "cache", "sehir": "İzmir", "cpu": 84},
]
ONCELIKLER = ["düşük", "orta", "yüksek", "kritik"]
FORM_KULLANICI = {"ayse": "pafta-demo"}
BASIC_KULLANICI = {"yonetici": "pafta-demo", "ayse": "pafta-demo"}
BASIC_YETKILI = {"yonetici"}
JETON = "demo-jeton-123"
OTURUM = "s7f3a-ayse"
AZAMI_GOVDE = 4096
SINIR = 3
DURUM_ETAG = '"v241"'
RAPOR_DEGISTI = "Sun, 18 Oct 2026 22:00:00 GMT"
KISA = {"w1": "/sunucular/web01", "db": "/sunucular/db01"}


class Durum:
    def __init__(self):
        self.biletler = {1: {"id": 1, "baslik": "Disk dolu", "oncelik": "yüksek"},
                         2: {"id": 2, "baslik": "Yedek gecikti", "oncelik": "orta"}}
        self.sonraki = 3
        self.sinir = 0
        self.kilit = threading.Lock()


def _sayfa(baslik, govde, ek_bas=""):
    return ("<!DOCTYPE html>\n<html lang=\"tr\">\n<head>\n  <meta charset=\"utf-8\">\n"
            f"  <title>{baslik} · Pafta Bilet Masası</title>\n{ek_bas}</head>\n<body>\n{govde}</body>\n</html>\n")


ANA_SAYFA = _sayfa("Ana sayfa", """<!-- sürüm 2.4.1 · ön yüz ekibi -->
<h1>Pafta Bilet Masası</h1>
<nav>
  <a href="/sunucular">Sunucular</a>
  <a href="/bilet-ac">Bilet aç</a>
  <a href="giris">Giriş</a>
  <a href="https://belgeler.pafta.test/api">API belgeleri</a>
</nav>
<p>Açık bilet sayısı: <strong id="acik">2</strong></p>
""", '  <meta name="description" content="Altyapı ekibinin bilet masası">\n'
     '  <link rel="stylesheet" href="/static/site.css">\n')

BILET_FORMU = _sayfa("Bilet aç", """<h1>Yeni bilet</h1>
<form action="/bilet-ac" method="post">
  <input type="hidden" name="form_kodu" value="fk-1029">
  <label>Başlık <input type="text" name="baslik" required maxlength="80"></label>
  <label>Öncelik
    <select name="oncelik">
      <option value="düşük">Düşük</option>
      <option value="orta" selected>Orta</option>
      <option value="yüksek">Yüksek</option>
      <option value="kritik">Kritik</option>
    </select>
  </label>
  <label>Kaynak <input type="text" name="kaynak" value="web" disabled></label>
  <label><input type="checkbox" name="acil" value="evet"> Acil</label>
  <textarea name="aciklama" rows="3"></textarea>
  <button type="submit" name="islem" value="kaydet">Kaydet</button>
</form>
""")

GIRIS_FORMU = _sayfa("Giriş", """<h1>Giriş</h1>
<form action="/giris" method="post">
  <input type="hidden" name="form_kodu" value="fk-2210">
  <input type="text" name="kullanici" autocomplete="username">
  <input type="password" name="parola" autocomplete="current-password">
  <button type="submit">Giriş yap</button>
</form>
""")

KAYNAKLAR = _sayfa("Kaynaklar", """<h1>Kaynaklar</h1>
<!-- not: eski uç nokta /v1/durum kaldırıldı, /durum kullanılıyor -->
<ul id="liste" data-sayfa="1" data-sayfa-boyu="20">
  <li data-sunucu="web01"><a href="/sunucular/web01">web01</a></li>
  <li data-sunucu="db01"><a href="../sunucular/db01">db01</a></li>
</ul>
<img src="/static/logo.png" alt="Pafta">
<script type="application/json" id="ayarlar">{"api": "/api/rapor", "surum": "2.4.1", "yenileme_sn": 30}</script>
<script src="/static/uygulama.js" defer></script>
""")


class Isleyici(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PaftaSunucu/1.0"
    timeout = 5

    def version_string(self):
        return self.server_version

    def date_time_string(self, timestamp=None):
        return TARIH

    def log_message(self, *args):
        pass

    def do_GET(self):
        self._isle()

    do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_GET

    # — yanıt yardımcıları —
    def _yanit(self, kod, govde=b"", tur=None, basliklar=()):
        if isinstance(govde, (dict, list)):
            govde = json.dumps(govde, ensure_ascii=False).encode("utf-8")
            tur = tur or "application/json; charset=utf-8"
        elif isinstance(govde, str):
            govde = govde.encode("utf-8")
            tur = tur or "text/plain; charset=utf-8"
        self.send_response(kod)
        bossuz = kod not in (204, 304)
        if tur and bossuz:
            self.send_header("Content-Type", tur)
        for ad, deger in basliklar:
            self.send_header(ad, deger)
        if bossuz:
            self.send_header("Content-Length", str(len(govde)))
        istemci_kapatiyor = "close" in [t.strip().lower() for t in self.headers.get("Connection", "").split(",")]
        if self._kapat or istemci_kapatiyor:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        if self.command != "HEAD" and bossuz:
            self.wfile.write(govde)

    def _html(self, kod, sayfa, basliklar=()):
        self._yanit(kod, sayfa, "text/html; charset=utf-8", basliklar)

    def _yonlendir(self, kod, yer, basliklar=()):
        self._yanit(kod, b"", None, [("Location", yer)] + list(basliklar))

    def _govde(self):
        """→ (bayt, hata_kodu). Content-Length ya da chunked; ikisi de yoksa 411. Gövde okunamazsa
        bağlantı kapatılır: okunmamış baytlar bir sonraki istek sanılmasın."""
        bayt, kod = self._govde_oku()
        self._okundu = True
        if kod:
            self._kapat = True
        return bayt, kod

    def _govde_oku(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            parcalar = []
            while True:
                satir = self.rfile.readline(100).strip()
                try:
                    n = int(satir.split(b";")[0], 16)
                except ValueError:
                    return None, 400
                if n == 0:
                    self.rfile.readline(100)
                    break
                parcalar.append(self.rfile.read(n))
                self.rfile.readline(100)
                if sum(map(len, parcalar)) > AZAMI_GOVDE:
                    return None, 413
            return b"".join(parcalar), None
        n = self.headers.get("Content-Length")
        if n is None:
            return None, 411
        if not n.strip().isdigit():
            return None, 400
        n = int(n)
        if n > AZAMI_GOVDE:
            return None, 413
        return self.rfile.read(n), None

    def _hata(self, kod, mesaj, basliklar=()):
        self._yanit(kod, {"hata": mesaj}, basliklar=basliklar)

    def _cerezler(self):
        out = {}
        for parca in self.headers.get("Cookie", "").split(";"):
            ad, esit, deger = parca.strip().partition("=")
            if esit:
                out[ad] = deger
        return out

    # — yönlendirici —
    def _isle(self):
        self._okundu = self._kapat = False
        try:
            self._yonlendirici()
        finally:
            if not self._okundu and (self.headers.get("Content-Length") or self.headers.get("Transfer-Encoding")):
                self.close_connection = True       # rota gövdeyi okumadı: kalan baytlar yeni istek sanılmasın

    def _yonlendirici(self):
        if self.request_version == "HTTP/1.1" and not self.headers.get("Host"):
            return self._hata(400, "Host başlığı gerekli")
        u = urlsplit(self.path)
        self.yol, self.sorgu = u.path, dict(parse_qsl(u.query, keep_blank_values=True))
        for desen, yontemler, isim in ROTALAR:
            m = re.fullmatch(desen, self.yol)
            if not m:
                continue
            izinli = list(yontemler) + (["HEAD"] if "GET" in yontemler else []) + ["OPTIONS"]
            if self.command == "OPTIONS" and isim != "yanki":
                return self._yanit(204, basliklar=[("Allow", ", ".join(izinli))])
            if self.command not in izinli:
                return self._yanit(405, {"hata": f"{self.command} bu adreste desteklenmiyor"},
                                   basliklar=[("Allow", ", ".join(izinli))])
            return getattr(self, "r_" + isim)(*m.groups())
        self._hata(404, "sayfa bulunamadı")

    # — rotalar —
    def r_ana(self):
        self._html(200, ANA_SAYFA)

    def r_durum(self):
        bas = [("ETag", DURUM_ETAG), ("Cache-Control", "max-age=60")]
        istenen = [e.strip() for e in self.headers.get("If-None-Match", "").split(",") if e.strip()]
        if DURUM_ETAG in istenen or "*" in istenen:
            return self._yanit(304, basliklar=bas)
        self._yanit(200, {"durum": "ok", "surum": SURUM}, basliklar=bas)

    def r_sunucular(self):
        liste = SUNUCULAR
        if "rol" in self.sorgu:
            liste = [s for s in liste if s["rol"] == self.sorgu["rol"].lower()]
        if "min_cpu" in self.sorgu:
            if not self.sorgu["min_cpu"].isdigit():
                return self._hata(400, "min_cpu bir tam sayı olmalı")
            liste = [s for s in liste if s["cpu"] >= int(self.sorgu["min_cpu"])]
        kabul = self.headers.get("Accept", "")
        if "text/html" in kabul and "application/json" not in kabul:
            satirlar = "".join(f"  <tr><td>{s['ad']}</td><td>{s['rol']}</td><td>{s['cpu']}</td></tr>\n" for s in liste)
            return self._html(200, _sayfa("Sunucular", f"<table>\n{satirlar}</table>\n"), [("Vary", "Accept")])
        self._yanit(200, liste, basliklar=[("Vary", "Accept")])

    def r_sunucu(self, ad):
        s = next((s for s in SUNUCULAR if s["ad"] == ad), None)
        if s is None:
            return self._hata(404, "sunucu bulunamadı")
        self._yanit(200, s)

    def _bilet_girdisi(self, ham, tur):
        """→ (sözlük, None) ya da (None, (kod, mesaj))"""
        tur = tur.split(";")[0].strip().lower()
        if tur == "application/json":
            try:
                veri = json.loads(ham.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return None, (400, "gövde geçerli JSON değil")
            if not isinstance(veri, dict):
                return None, (400, "gövde bir JSON nesnesi olmalı")
        elif tur == "application/x-www-form-urlencoded":
            veri = dict(parse_qsl(ham.decode("utf-8", "replace"), keep_blank_values=True))
        else:
            return None, (415, "Content-Type application/json ya da application/x-www-form-urlencoded olmalı")
        baslik = veri.get("baslik")
        if not isinstance(baslik, str) or not 1 <= len(baslik.strip()) <= 80:
            return None, (422, "başlık 1-80 karakter olmalı")
        oncelik = veri.get("oncelik", "orta")
        if oncelik not in ONCELIKLER:
            return None, (422, "geçersiz öncelik")
        return {"baslik": baslik.strip(), "oncelik": oncelik}, None

    def _bilet_ekle(self, girdi):
        d = self.server.durum
        with d.kilit:
            b = dict(id=d.sonraki, **girdi)
            d.biletler[d.sonraki] = b
            d.sonraki += 1
        return b

    def r_biletler(self):
        d = self.server.durum
        if self.command in ("GET", "HEAD"):
            return self._yanit(200, list(d.biletler.values()))
        ham, kod = self._govde()
        if kod:
            return self._hata(kod, {411: "Content-Length gerekli", 413: f"gövde en fazla {AZAMI_GOVDE} bayt olabilir",
                                    400: "Content-Length geçersiz"}[kod])
        girdi, hata = self._bilet_girdisi(ham, self.headers.get("Content-Type", ""))
        if hata:
            return self._hata(*hata)
        b = self._bilet_ekle(girdi)
        self._yanit(201, b, basliklar=[("Location", f"/biletler/{b['id']}")])

    def r_bilet(self, no):
        d = self.server.durum
        no = int(no)
        if no not in d.biletler:
            return self._hata(404, "bilet bulunamadı")
        if self.command in ("GET", "HEAD"):
            return self._yanit(200, d.biletler[no])
        if self.command == "DELETE":
            with d.kilit:
                del d.biletler[no]
            return self._yanit(204)
        ham, kod = self._govde()
        if kod:
            return self._hata(kod, "gövde okunamadı")
        girdi, hata = self._bilet_girdisi(ham, self.headers.get("Content-Type", ""))
        if hata:
            return self._hata(*hata)
        with d.kilit:
            d.biletler[no] = dict(id=no, **girdi)
        self._yanit(200, d.biletler[no])

    def r_yanki(self):
        ham = b""
        if self.headers.get("Content-Length") or self.headers.get("Transfer-Encoding"):
            ham, kod = self._govde()
            if kod:
                return self._hata(kod, "gövde okunamadı")
        self._yanit(200, {"yontem": self.command, "yol": self.yol, "sorgu": self.sorgu,
                          "basliklar": [[a, d] for a, d in self.headers.items()],
                          "govde": ham.decode("utf-8", "replace")})

    def r_eski_panel(self):
        self._yonlendir(301, "/panel")

    def r_kisa(self, kod):
        if kod not in KISA:
            return self._hata(404, "kısa bağlantı bulunamadı")
        self._yonlendir(302, KISA[kod])

    def r_goreli(self):
        self._yonlendir(302, "sunucular?rol=web")

    def r_tasindi(self):
        self._yonlendir(307, "/biletler")

    def r_kalici(self):
        self._yonlendir(308, "/biletler")

    def r_dongu(self):
        self._yonlendir(302, "/dongu")

    def r_son_rapor(self):
        self._yonlendir(303, "/rapor.csv")

    def r_zincir(self, n):
        n = int(n)
        if n == 0:
            return self._yanit(200, "vardın\n")
        self._yonlendir(302, f"/zincir/{n - 1}")

    def r_bilet_ac(self):
        if self.command in ("GET", "HEAD"):
            return self._html(200, BILET_FORMU)
        ham, kod = self._govde()
        if kod:
            return self._hata(kod, "gövde okunamadı")
        girdi, hata = self._bilet_girdisi(ham, self.headers.get("Content-Type", ""))
        if hata:
            return self._html(hata[0], _sayfa("Bilet aç", f"<p class=\"hata\">{html.escape(hata[1])}</p>\n"))
        b = self._bilet_ekle(girdi)
        self._yonlendir(303, f"/biletler/{b['id']}")

    def r_tercih(self):
        tema = self.sorgu.get("tema")
        if tema is None:
            return self._yanit(200, {"tema": self._cerezler().get("tema", "acik")})
        if tema not in ("acik", "koyu"):
            return self._hata(400, "tema acik ya da koyu olmalı")
        self._yanit(200, {"tema": tema},
                    basliklar=[("Set-Cookie", f"tema={tema}; Path=/; Max-Age=31536000; SameSite=Lax")])

    def r_giris(self):
        if self.command in ("GET", "HEAD"):
            return self._html(200, GIRIS_FORMU)
        ham, kod = self._govde()
        if kod:
            return self._hata(kod, "gövde okunamadı")
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/x-www-form-urlencoded":
            return self._hata(415, "form gövdesi bekleniyor")
        veri = dict(parse_qsl(ham.decode("utf-8", "replace"), keep_blank_values=True))
        if not veri.get("kullanici") or not veri.get("parola"):
            return self._html(400, _sayfa("Giriş", "<p class=\"hata\">Kullanıcı adı ve parola gerekli.</p>\n"))
        if FORM_KULLANICI.get(veri["kullanici"]) != veri["parola"]:
            return self._html(401, _sayfa("Giriş", "<p class=\"hata\">Kullanıcı adı ya da parola yanlış.</p>\n"))
        self._yonlendir(303, "/panel",
                        [("Set-Cookie", f"oturum={OTURUM}; Path=/; HttpOnly; SameSite=Strict")])

    def r_panel(self):
        if self._cerezler().get("oturum") != OTURUM:
            return self._yonlendir(302, "/giris")
        self._html(200, _sayfa("Panel", "<h1>Hoş geldin, ayse</h1>\n<form action=\"/cikis\" method=\"post\"><button>Çıkış</button></form>\n"))

    def r_cikis(self):
        self._yonlendir(303, "/", [("Set-Cookie", "oturum=; Path=/; Max-Age=0")])

    def r_yonetim(self):
        istem = [("WWW-Authenticate", 'Basic realm="Pafta Yonetim"')]
        yetki = self.headers.get("Authorization", "")
        tur, _, kimlik = yetki.partition(" ")
        if tur.lower() != "basic":
            return self._hata(401, "kimlik bilgisi gerekli", istem)
        try:
            kullanici, iki_nokta, parola = base64.b64decode(kimlik.strip(), validate=True).decode("utf-8").partition(":")
        except ValueError:
            return self._hata(401, "kimlik bilgisi okunamadı", istem)
        if not iki_nokta or BASIC_KULLANICI.get(kullanici) != parola:
            return self._hata(401, "kullanıcı adı ya da parola yanlış", istem)
        if kullanici not in BASIC_YETKILI:
            return self._hata(403, "bu sayfa için yetkin yok")
        self._yanit(200, {"kullanici": kullanici, "rol": "yonetici"})

    def r_rapor(self):
        tur, _, jeton = self.headers.get("Authorization", "").partition(" ")
        if tur.lower() != "bearer" or not jeton:
            return self._hata(401, "jeton gerekli", [("WWW-Authenticate", 'Bearer realm="pafta"')])
        if jeton.strip() != JETON:
            return self._hata(401, "jeton geçersiz", [("WWW-Authenticate", 'Bearer realm="pafta", error="invalid_token"')])
        self._yanit(200, {"rapor": "haftalik", "acik_bilet": len(self.server.durum.biletler)})

    def r_hata(self):
        self._hata(500, "beklenmeyen bir sorun oluştu")

    def r_bakim(self):
        self._hata(503, "bakım çalışması var", [("Retry-After", "120")])

    def r_sinir(self):
        d = self.server.durum
        with d.kilit:
            d.sinir += 1
            n = d.sinir
        if n > SINIR:
            return self._hata(429, "çok fazla istek", [("Retry-After", "30")])
        self._yanit(200, {"kalan": SINIR - n}, basliklar=[("X-Kalan-Hak", str(SINIR - n))])

    def r_v1_durum(self):
        self._hata(410, "bu uç nokta kaldırıldı; /durum kullan")

    def r_rapor_csv(self):
        bas = [("Last-Modified", RAPOR_DEGISTI)]
        istenen = self.headers.get("If-Modified-Since")
        if istenen:
            try:
                if email.utils.parsedate_to_datetime(istenen) >= email.utils.parsedate_to_datetime(RAPOR_DEGISTI):
                    return self._yanit(304, basliklar=bas)
            except (TypeError, ValueError):
                pass
        self._yanit(200, "sunucu,acik_bilet\nweb01,1\ndb01,1\n", "text/csv; charset=utf-8", bas)

    def r_sikistirilmis(self):
        metin = ("Pafta Bilet Masası haftalık özeti. " * 8).encode("utf-8")
        bas = [("Vary", "Accept-Encoding")]
        if "gzip" in self.headers.get("Accept-Encoding", "").lower():
            return self._yanit(200, gzip.compress(metin, mtime=0), "text/plain; charset=utf-8",
                               bas + [("Content-Encoding", "gzip")])
        self._yanit(200, metin, "text/plain; charset=utf-8", bas)

    def r_akis(self):
        parcalar = ["ilk satır\n", "ikinci satır\n", "son\n"]
        if self.request_version != "HTTP/1.1":
            return self._yanit(200, "".join(parcalar))
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        if self.command == "HEAD":
            return
        for p in parcalar:
            b = p.encode("utf-8")
            self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
        self.wfile.write(b"0\r\n\r\n")

    def r_kaynaklar(self):
        self._html(200, KAYNAKLAR)


ROTALAR = [
    (r"/", ("GET",), "ana"),
    (r"/durum", ("GET",), "durum"),
    (r"/sunucular", ("GET",), "sunucular"),
    (r"/sunucular/([\w-]+)", ("GET",), "sunucu"),
    (r"/biletler", ("GET", "POST"), "biletler"),
    (r"/biletler/(\d+)", ("GET", "PUT", "DELETE"), "bilet"),
    (r"/yanki", ("GET", "POST", "PUT", "PATCH", "DELETE"), "yanki"),
    (r"/eski-panel", ("GET",), "eski_panel"),
    (r"/kisa/(\w+)", ("GET",), "kisa"),
    (r"/goreli", ("GET",), "goreli"),
    (r"/tasindi", ("GET", "POST"), "tasindi"),
    (r"/kalici", ("GET", "POST"), "kalici"),
    (r"/dongu", ("GET",), "dongu"),
    (r"/son-rapor", ("GET",), "son_rapor"),
    (r"/zincir/(\d+)", ("GET",), "zincir"),
    (r"/bilet-ac", ("GET", "POST"), "bilet_ac"),
    (r"/tercih", ("GET",), "tercih"),
    (r"/giris", ("GET", "POST"), "giris"),
    (r"/panel", ("GET",), "panel"),
    (r"/cikis", ("POST",), "cikis"),
    (r"/yonetim", ("GET",), "yonetim"),
    (r"/api/rapor", ("GET",), "rapor"),
    (r"/hata", ("GET",), "hata"),
    (r"/bakim", ("GET",), "bakim"),
    (r"/sinir", ("GET",), "sinir"),
    (r"/v1/durum", ("GET",), "v1_durum"),
    (r"/rapor\.csv", ("GET",), "rapor_csv"),
    (r"/sikistirilmis", ("GET",), "sikistirilmis"),
    (r"/akis", ("GET",), "akis"),
    (r"/kaynaklar", ("GET",), "kaynaklar"),
]


class Yanit:
    """Ham HTTP yanıtının ayrıştırılmış hâli."""

    def __init__(self, ham):
        self.ham_bayt = ham
        self.ham = ham.decode("utf-8", "replace")
        bas, _, govde = ham.partition(b"\r\n\r\n")
        satirlar = bas.decode("iso-8859-1").split("\r\n")
        parcalar = satirlar[0].split(" ", 2)
        self.surum = parcalar[0] if parcalar[0] else None
        self.durum = int(parcalar[1]) if len(parcalar) > 1 and parcalar[1].isdigit() else None
        self.neden = parcalar[2] if len(parcalar) > 2 else ""
        self.basliklar = [(a.strip(), d.strip()) for a, _, d in (s.partition(":") for s in satirlar[1:] if s)]
        uzunluk = self.baslik("Content-Length")
        self.kalan_bayt = b""                      # Content-Length'ten sonra gelenler (ör. ikinci bir yanıt)
        if uzunluk and uzunluk.isdigit():
            govde, self.kalan_bayt = govde[:int(uzunluk)], govde[int(uzunluk):]
        self.govde_bayt = govde
        self.govde = govde.decode("utf-8", "replace")

    def baslik(self, ad):
        return next((d for a, d in self.basliklar if a.lower() == ad.lower()), None)

    def hepsi(self, ad):
        return [d for a, d in self.basliklar if a.lower() == ad.lower()]

    def json(self):
        return json.loads(self.govde)

    def __repr__(self):
        return f"<Yanit {self.durum} {self.neden}>"


def _kur():
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    sunucu.daemon_threads = True
    sunucu.durum = Durum()
    sunucu.handle_error = lambda istek, adres: None        # iş parçacığı hataları kullanıcı çıktısına karışmasın
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    host, port = sunucu.server_address[:2]

    def gonder_bayt(istek, zaman_asimi=3):
        if isinstance(istek, str):
            istek = istek.encode("utf-8")
        parcalar = []
        with socket.create_connection((host, port), timeout=zaman_asimi) as s:
            s.sendall(istek)
            s.shutdown(socket.SHUT_WR)             # başka istek yok: sunucu yanıtlayıp bağlantıyı kapatır
            while True:
                try:
                    p = s.recv(65536)
                except socket.timeout:
                    break
                if not p:
                    break
                parcalar.append(p)
        return b"".join(parcalar)

    m = types.ModuleType("tezgah")
    m.__doc__ = __doc__
    m.HOST, m.PORT, m.SUNUCU = host, port, f"http://{host}:{port}"
    m.gonder_bayt = gonder_bayt
    m.gonder = lambda istek, zaman_asimi=3: gonder_bayt(istek, zaman_asimi).decode("utf-8", "replace")
    m.yanit = lambda istek, zaman_asimi=3: Yanit(gonder_bayt(istek, zaman_asimi))
    m.Yanit = Yanit
    sys.modules["tezgah"] = m


_kur()
