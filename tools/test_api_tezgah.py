"""sandbox/api_tezgah.py duman testi: P74, PS23 ve BS29'un yerel API laboratuvarı.

    python tools/test_api_tezgah.py

Sunucuyu bu süreçte başlatır (127.0.0.1, boş port), internete çıkmaz.
"""
import json
from pathlib import Path
import runpy
import sys
import threading
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "sandbox" / "api_tezgah.py"), run_name="__tezgah__")
api = sys.modules["api"]


class Istemci:
    def __init__(self):
        self.cerez = {}

    def iste(self, yol, veri=None, cerezli=True):
        r = urllib.request.Request(api.SUNUCU + yol)
        if veri is not None:
            r.data = json.dumps(veri, ensure_ascii=False).encode()
            r.add_header("Content-Type", "application/json")
        if cerezli and self.cerez:
            r.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in self.cerez.items()))
        try:
            with urllib.request.urlopen(r, timeout=5) as y:
                kod, basliklar, govde = y.status, dict(y.headers), y.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            kod, basliklar, govde = e.code, dict(e.headers), e.read().decode("utf-8")
        sc = basliklar.get("Set-Cookie")
        if sc:
            ad, _, kalan = sc.partition("=")
            self.cerez[ad] = kalan.split(";")[0]
        return kod, basliklar, govde

    def json(self, yol, veri=None, cerezli=True):
        kod, basliklar, govde = self.iste(yol, veri, cerezli)
        return kod, basliklar, (json.loads(govde) if govde else None)


class OturumVeListe(unittest.TestCase):
    def setUp(self):
        self.i = Istemci()

    def giris(self):
        return self.i.json("/giris", {"kullanici": "analist", "parola": "pafta123"})

    def test_oturumsuz_liste_401(self):
        self.assertEqual(self.i.json("/api/biletler")[::2], (401, {"hata": "oturum"}))

    def test_yanlis_parola_401(self):
        kod, _, d = self.i.json("/giris", {"kullanici": "analist", "parola": "yanlis"})
        self.assertEqual((kod, d), (401, {"hata": "kimlik"}))

    def test_giris_cerez_ve_sabit_tarih(self):
        kod, basliklar, _ = self.giris()
        self.assertEqual(kod, 200)
        self.assertIn("oturum", self.i.cerez)
        self.assertEqual(basliklar.get("Date"), "Mon, 19 Oct 2026 09:00:00 GMT")

    def test_sayfalama_sinirlari(self):
        self.giris()
        _, _, d = self.i.json("/api/biletler")
        self.assertEqual((d["sayfa"], d["sonraki"], [b["id"] for b in d["kayitlar"]]), (1, 2, [101, 102, 103]))
        self.assertGreaterEqual(d["toplam"], 7, "yedi hazır kayıt (aynı süreçteki başka test kayıt ekleyebilir)")
        _, _, d = self.i.json("/api/biletler?sayfa=3")
        self.assertEqual([b["id"] for b in d["kayitlar"]][0], 107)
        kod, _, d = self.i.json("/api/biletler?sayfa=9")
        self.assertEqual((kod, d["kayitlar"]), (200, []))
        self.assertEqual(self.i.json("/api/biletler?sayfa=0")[::2], (400, {"hata": "sayfa"}))

    def test_tek_bilet_ve_404(self):
        self.giris()
        self.assertEqual(self.i.json("/api/bilet/104")[2]["baslik"], "web02 sertifika süresi")
        self.assertEqual(self.i.json("/api/bilet/999")[::2], (404, {"hata": "yok"}))


class Olusturma(unittest.TestCase):
    def test_alan_oncelik_yinelenen_ve_201(self):
        i = Istemci()
        i.json("/giris", {"kullanici": "analist", "parola": "pafta123"})
        self.assertEqual(i.json("/api/bilet", {"baslik": "", "oncelik": "orta"})[::2], (400, {"hata": "alan"}))
        self.assertEqual(i.json("/api/bilet", {"baslik": "x", "oncelik": "acil"})[::2], (400, {"hata": "oncelik"}))
        kod, _, d = i.json("/api/bilet", {"baslik": "Web01 Disk Doldu", "oncelik": "orta"})
        self.assertEqual((kod, d["hata"]), (409, "yinelenen"), "başlık büyük-küçük harfe bakılmadan yinelenir")
        kod, basliklar, d = i.json("/api/bilet", {"baslik": "test_api_tezgah kaydı", "oncelik": "yüksek"})
        self.assertEqual(kod, 201)
        self.assertEqual(basliklar.get("Location"), f"/api/bilet/{d['id']}")


class DigerUclar(unittest.TestCase):
    def setUp(self):
        self.i = Istemci()

    def test_durum_ucu_esikleri(self):
        self.assertEqual(self.i.json("/durum/503")[0], 503)
        self.assertEqual(self.i.json("/durum/400")[2]["hata"], "istek")
        self.assertEqual(self.i.json("/durum/399")[::2], (400, {"hata": "kod"}))
        self.assertEqual(self.i.json("/durum/600")[::2], (400, {"hata": "kod"}))

    def test_html_sayfalari(self):
        kod, _, g = self.i.iste("/sayfa/biletler")
        self.assertEqual(kod, 200)
        self.assertIn('id="biletler"', g)
        self.assertIn('name="belirtec"', g)
        self.assertIn("kapanmamış", self.i.iste("/sayfa/bozuk")[2])

    def test_bos_204(self):
        kod, _, g = self.i.iste("/bos")
        self.assertEqual((kod, g), (204, ""))

    def test_yavas_ve_eszamanli(self):
        self.i.json("/eszamanli")                           # önceki ölçümü sıfırla
        self.assertEqual(self.i.json("/yavas?ms=2001")[::2], (400, {"hata": "ms"}))
        sonuc = []
        isler = [threading.Thread(target=lambda n=n: sonuc.append(self.i.json(f"/yavas?ms=300&no={n}")[2]["no"]))
                 for n in range(1, 4)]
        for t in isler:
            t.start()
        for t in isler:
            t.join()
        self.assertEqual(sorted(sonuc), [1, 2, 3])
        self.assertEqual(self.i.json("/eszamanli")[2], {"en_cok": 3}, "üç istek aynı anda beklemiş olmalı")
        self.assertEqual(self.i.json("/eszamanli")[2], {"en_cok": 0}, "okununca sıfırlanır")


if __name__ == "__main__":
    unittest.main()
