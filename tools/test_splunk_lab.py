# -*- coding: utf-8 -*-
"""SPL yolunun gerçek Splunk laboratuvarı (sandbox/splunk_lab.py, py_harness spk_*).

Docker çalışmıyorsa ya da Splunk konteyneri kurulamıyorsa testler atlanır.

    python tools/test_splunk_lab.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.runners import for_step, get  # noqa: E402
from sandbox import splunk_lab  # noqa: E402

PROPS = {"meta": {"motor": "splunk", "girdi": "props"}}
ARAMA = {"meta": {"motor": "splunk"}}
VERI = 'veri("2026-10-19 09:01:12,345 ERROR a\\n  devam\\n2026-10-19 09:02:00,001 INFO b\\n", "pafta_t")\n'
KITA = ("[pafta_t]\nSHOULD_LINEMERGE = false\nLINE_BREAKER = ([\\r\\n]+)(?=\\d{4}-)\n"
        "TIME_PREFIX = ^\nTIME_FORMAT = %Y-%m-%d %H:%M:%S,%3N\n")


class Takvim(unittest.TestCase):
    """Splunk gerektirmeyen parçalar: cron ayrıştırma ve alarm girdisinin gün kaydırması."""

    def setUp(self):
        from sandbox import py_harness
        self.H = py_harness

    def anlar(self, cron, bas, son):
        return [self.H._an_yaz(a) for a in self.H._cron_anlari(cron, self.H._an(bas), self.H._an(son))]

    def test_cron(self):
        self.assertEqual(self.anlar("*/30 * * * *", "2026-10-19 09:00", "2026-10-19 10:30"),
                         ["2026-10-19 09:00", "2026-10-19 09:30", "2026-10-19 10:00", "2026-10-19 10:30"])
        self.assertEqual(self.anlar("5,50 9-10 * * *", "2026-10-19 08:00", "2026-10-19 11:00"),
                         ["2026-10-19 09:05", "2026-10-19 09:50", "2026-10-19 10:05", "2026-10-19 10:50"])
        self.assertEqual(self.anlar("10/20 * * * *", "2026-10-19 09:00", "2026-10-19 09:59"),
                         ["2026-10-19 09:10", "2026-10-19 09:30", "2026-10-19 09:50"])
        for yanlis in ("* * *", "*/0 * * * *", "61 * * * *", "0 9 * * 1"):
            with self.assertRaises(ValueError, msg=yanlis):
                self.H._cron_anlari(yanlis, 0, 3600)

    def test_gun_kaydirma(self):
        gun = 86400
        self.assertEqual(self.H._gun_kaydir("2026-10-19 09:01 a=2026-10-19\n  2026-10-19 x\n", 6 * gun),
                         "2026-10-25 09:01 a=2026-10-19\n  2026-10-19 x\n", "yalnız satır başındaki tarih kayar")
        self.assertEqual(self.H._an_yaz("2026-10-25T09:15:00.000+00:00", 6 * gun), "2026-10-19 09:15")


def setUpModule():
    sorun = splunk_lab.hazirla() if splunk_lab.available() else "Docker yok"
    if sorun:
        Splunk.__unittest_skip__ = True
        Splunk.__unittest_skip_why__ = sorun


class Splunk(unittest.TestCase):
    def test_props_girdisi(self):
        r = for_step(get("spl"), PROPS).run(KITA, "", VERI)
        self.assertEqual(r["status"], "ok", r.get("error"))
        satirlar = r["tablolar"][0]["satirlar"]
        self.assertEqual([s[0] for s in satirlar], ["2026-10-19 09:01:12.345", "2026-10-19 09:02:00.001"])
        self.assertIn("devam", satirlar[0][2], "devam satırı ilk olayda kalır")

    def test_props_hatalari(self):
        r = for_step(get("spl"), PROPS).run("[baska]\nTZ = UTC\n", "", VERI)
        self.assertIn("pafta_", r["error"]["msg"])
        r = for_step(get("spl"), PROPS).run("TZ = UTC\n", "", VERI)
        self.assertIn("kıta", r["error"]["msg"])

    def test_arama_ve_test(self):
        adim = dict(ARAMA, setup="props('pafta_t', {'SHOULD_LINEMERGE': 'false'})\n" + VERI,
                    test="eq(sutunlar, ['n'], 'alan')\neq(sonuc, [(3,)], 'üç satır')\n"
                         "eq(dene(\"veri('2026-10-19 10:00:00 x\\\\n', 'pafta_t')\"), [(4,)], 'dene ekler')")
        r = for_step(get("spl"), adim).test(f"index={splunk_lab.DIZIN} | stats count AS n", adim)
        self.assertEqual(r["status"], "pass", (r.get("checks"), r.get("error")))
        r = for_step(get("spl"), ARAMA).run("index=pafta_ders | bilinmeyenkomut", "", "")
        self.assertEqual(r["status"], "error")

    def test_alarm_girdisi(self):
        hazirlik = ("props('pafta_t', {'SHOULD_LINEMERGE': 'false', 'TIME_PREFIX': '^', 'TIME_FORMAT': '%Y-%m-%d %H:%M'})\n"
                    "veri('2026-10-19 09:01 d=1\\n2026-10-19 09:20 d=1\\n', 'pafta_t')\n"
                    "aralik('2026-10-19 09:00', '2026-10-19 09:30')\n")
        kod = (f"[pafta_k]\nsearch = index={splunk_lab.DIZIN} d=1 | stats count | where count > 0\ncron_schedule = */15 * * * *\n"
               "dispatch.earliest_time = -15m\ndispatch.latest_time = now\ncounttype = number of events\n"
               "relation = greater than\nquantity = 0\nalert.track = 1\nalert.suppress = 1\nalert.suppress.period = 1h\n")
        r = for_step(get("spl"), {"meta": {"motor": "splunk", "girdi": "alarm"}}).run(kod, "", hazirlik)
        self.assertEqual(r["status"], "ok", r.get("error"))
        self.assertEqual([s[1:] for s in r["tablolar"][0]["satirlar"]],
                         [["2026-10-19 09:00", "2026-10-19 08:45", "2026-10-19 09:00", "0", "0", "0", ""],
                          ["2026-10-19 09:15", "2026-10-19 09:00", "2026-10-19 09:15", "1", "1", "0", "1"],
                          ["2026-10-19 09:30", "2026-10-19 09:15", "2026-10-19 09:30", "1", "0", "1", ""]],
                         "pencere başı dahil sonu hariç; ikinci alarm bastırılır; tarihler dersinkiler")
        r = for_step(get("spl"), {"meta": {"motor": "splunk", "girdi": "alarm"}}).run(
            kod.replace("cron_schedule = */15 * * * *\n", ""), "", hazirlik)
        self.assertIn("cron_schedule", r["error"]["msg"])

    def test_bos_laboratuvar(self):
        r = for_step(get("spl"), ARAMA).run(f"index={splunk_lab.DIZIN} | stats count", "", "")
        self.assertEqual(r["tablolar"][0]["satirlar"], [["0"]], "önceki işin verisi temizlenmiş")


if __name__ == "__main__":
    unittest.main(verbosity=1)
