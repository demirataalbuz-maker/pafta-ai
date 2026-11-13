# -*- coding: utf-8 -*-
"""Ağ Tespiti laboratuvarı (sandbox/ids_lab.py, ids_trafik.py, py_harness ids_*).

WSL'de Suricata ve Scapy ya da Docker'da Zeek imajı yoksa testler atlanır.

    python tools/test_ids_lab.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.runners import for_step, get  # noqa: E402
from sandbox import ids_lab  # noqa: E402

TRAFIK = ('akis(tur="dns", zaman="2026-10-19 09:00:00", istemci="10.0.1.15", sunucu="10.0.0.2", ad="a.test", cevap="203.0.113.1")\n'
          'akis(tur="dns", zaman="2026-10-19 09:00:10", istemci="10.0.1.15", sunucu="10.0.0.2", ad="yok.test")\n'
          'akis(tur="http", zaman="2026-10-19 09:01:00", istemci="10.0.1.15", sunucu="203.0.113.1", '
          'istek="GET /x.pdf HTTP/1.1\\r\\nHost: a.test\\r\\n\\r\\n", yanit="HTTP/1.1 200 OK\\r\\nContent-Length: 0\\r\\n\\r\\n")\n')
SURICATA = {"setup": TRAFIK}
ZEEK = {"meta": {"motor": "zeek"}, "setup": TRAFIK}


def setUpModule():
    sorunlar = ids_lab.durum()
    if sorunlar:
        raise unittest.SkipTest("; ".join(sorunlar))


class Suricata(unittest.TestCase):
    def test_alarm(self):
        r = for_step(get("ids"), SURICATA).run(
            'alert http any any -> any any (msg:"pdf"; http.uri; content:".pdf"; endswith; sid:1;)\n', "", TRAFIK)
        self.assertEqual(r["status"], "ok", r.get("error"))
        self.assertEqual(r["tablolar"][0]["satirlar"], [["2026-10-19 09:01:00", "1", "pdf", "10.0.1.15", "203.0.113.1", "80"]],
                         "zaman UTC; Suricata'nın yerel saat dilimi sonucu kaydırmaz")

    def test_kural_hatalari(self):
        r = for_step(get("ids"), SURICATA).run('alert dns any any -> any any (msg:"x"; bilinmeyen; sid:1;)\n', "", TRAFIK)
        self.assertEqual(r["status"], "error")
        self.assertIn("bilinmeyen", r["error"]["msg"])
        r = for_step(get("ids"), SURICATA).run(
            'alert dns any any -> any any (msg:"a"; sid:1;)\nalert dns any any -> any any (msg:"b"; sid:1;)\n', "", TRAFIK)
        self.assertEqual((r["status"], r["error"]["line"]), ("error", 2), "aynı sid ikinci satırda reddedilir")
        r = for_step(get("ids"), SURICATA).run("# yalnız yorum\n", "", TRAFIK)
        self.assertIn("boş", r["error"]["msg"])

    def test_dene_trafik_ekler(self):
        adim = dict(SURICATA, test="eq(len(sonuc), 1, 'bir')\n"
                                   "eq(len(dene('akis(tur=\"dns\", zaman=\"2026-10-19 09:02:00\", istemci=\"10.0.1.16\", "
                                   "sunucu=\"10.0.0.2\", ad=\"b.yok.test\")')), 2, 'iki')")
        r = for_step(get("ids"), adim).test('alert dns any any -> any any (msg:"nx"; dns.rcode:3; sid:2;)\n', adim)
        self.assertEqual(r["status"], "pass", (r.get("checks"), r.get("error")))


class Zeek(unittest.TestCase):
    def test_betik_ve_gunlukler(self):
        adim = dict(ZEEK, test="eq(sonuc, [('a.test',), ('yok.test',)], 'print')\n"
                               "eq(sorted(k['query'] for k in kayitlar['dns']), ['a.test', 'yok.test'], 'dns.log')\n"
                               "eq(len(kayitlar['http']), 1, 'http.log')")
        kod = "event dns_request(c: connection, msg: dns_msg, query: string, qtype: count, qclass: count)\n\t{\n\tprint query;\n\t}\n"
        r = for_step(get("ids"), adim).test(kod, adim)
        self.assertEqual(r["status"], "pass", (r.get("checks"), r.get("error")))

    def test_hata_satiri(self):
        r = for_step(get("ids"), ZEEK).run("event zeek_init() { print bozuk; }\n", "", TRAFIK)
        self.assertEqual(r["status"], "error")
        self.assertEqual(r["error"]["line"], 1)
        self.assertIn("bozuk", r["error"]["msg"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
