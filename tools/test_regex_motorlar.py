# -*- coding: utf-8 -*-
"""Regex yolunun .NET ve JavaScript motorları (sandbox/regex_motorlar.py, motor: dotnet / javascript).

    python tools/test_regex_motorlar.py
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sandbox"))

import regex_motorlar as rm  # noqa: E402
from engine import runners  # noqa: E402

ORTAK = [  # dört motorda da aynı anlama gelen desenler
    (r"[0-9]+", "a1 b22 c333"),
    (r"x*", "axx"),
    (r"", "abc"),
    (r"(a)|(b)", "abc"),
    (r"(?<=\$)[0-9]+", "$12 ve $3"),
    (r"[a-z]+@[a-z]+", "ali@ornek ve ayse@pafta"),
]


class Motorlar(unittest.TestCase):
    def test_ortak_desenler_re_ile_ayni(self):
        for motor in ("dotnet", "javascript"):
            for desen, metin in ORTAK:
                with self.subTest(motor=motor, desen=desen):
                    a, b = re.compile(desen), rm.compile(desen, motor)
                    self.assertEqual([(m.span(), m.groups()) for m in a.finditer(metin)],
                                     [(m.span(), m.groups()) for m in b.finditer(metin)])
                    self.assertEqual(a.findall(metin), b.findall(metin))
                    self.assertEqual(a.split(metin), b.split(metin))

    def test_unicode_farklari(self):
        self.assertEqual(rm.compile(r"\d+", "dotnet").findall("1 ٣٤ ２"), ["1", "٣٤", "２"])
        self.assertEqual(rm.compile(r"\d+", "javascript").findall("1 ٣٤ ２"), ["1"])
        self.assertEqual(rm.compile(r"\w+", "javascript").findall("çay ışık"), ["ay", "k"])
        self.assertEqual(rm.compile(r"\w+", "dotnet").findall("çay ışık"), ["çay", "ışık"])

    def test_vekil_ciftleri(self):
        self.assertEqual(rm.compile("😀+", "dotnet").findall("😀😀 😀"), ["😀", "😀", "😀"])
        self.assertEqual(rm.compile("😀+", "javascript").findall("😀😀 😀"), ["😀😀", "😀"])
        self.assertEqual([(m.group(0), m.span()) for m in rm.compile(".", "dotnet").finditer("a😀")],
                         [("a", (0, 1)), ("�", (1, 2)), ("�", (1, 2))])

    def test_dotnet_grup_numaralari(self):
        d = rm.compile(r"(?<y>\d{4})-(?<a>\d{2})|x(y)?", "dotnet")
        self.assertEqual(d.groupindex, {"y": 2, "a": 3})
        self.assertEqual(d.search("2026-10").groups(), (None, "2026", "10"))
        j = rm.compile(r"(?<y>\d{4})-(?<a>\d{2})|x(y)?", "javascript")
        self.assertEqual(j.groupindex, {"y": 1, "a": 2})
        self.assertEqual(j.search("2026-10").groups(), ("2026", "10", None))

    def test_tam_eslesme_ve_satir_sonu(self):
        for motor in ("dotnet", "javascript"):
            d = rm.compile(r"[0-9]+", motor)
            self.assertIsNotNone(d.fullmatch("123"))
            self.assertIsNone(d.fullmatch("123\n"), motor)
            self.assertIsNone(d.match("a1"))
        self.assertEqual(rm.compile(r"ab$", "dotnet").findall("ab\n"), ["ab"])
        self.assertEqual(rm.compile(r"ab$", "javascript").findall("ab\n"), [])

    def test_derleme_hatalari(self):
        for motor, desen in (("dotnet", "("), ("dotnet", "a++"), ("javascript", "(?i)a"), ("javascript", "(?>a)")):
            with self.subTest(motor=motor, desen=desen), self.assertRaises(rm.RegexMotorHatasi):
                rm.compile(desen, motor)

    def test_dotnet_zaman_asimi(self):
        with self.assertRaises(rm.RegexMotorHatasi) as h:
            rm.compile(r"(a+)+$", "dotnet").search("a" * 35 + "!")
        self.assertIn("Timeout", h.exception.msg)

    def test_degistirme_python_sablonuyla(self):
        for motor in ("dotnet", "javascript"):
            d = rm.compile(r"(?<y>\d{4})-(?<a>\d{2})", motor)
            self.assertEqual(d.sub(r"\g<a>/\g<y>", "2026-10 ve 2025-01"), "10/2026 ve 01/2025")


class Kosucu(unittest.TestCase):
    def test_motor_secimi_ve_calistirma(self):
        for motor in ("dotnet", "javascript"):
            r = runners.for_step(runners.get("regex"), {"meta": {"motor": motor}})
            self.assertIsInstance(r, runners.RegexMotorRunner)
            res = r.run(r"\d+", "1 ٣٤")
            self.assertEqual(res["status"], "ok", res)
            beklenen = "1\n٣٤\n" if motor == "dotnet" else "1\n"
            self.assertEqual(res["segs"], [["out", beklenen]])
            adim = {"meta": {"motor": motor}, "test": "ok(tam('12') and not tam('12a'), 'tam')\neq(len(bul('1 2 3')), 3, 'bul')"}
            self.assertEqual(r.test(r"\d+", adim)["status"], "pass")
            hata = r.run("(", "x")
            self.assertEqual(hata["error"]["type"], "DesenHatası")
        sinir = runners.for_step(runners.get("regex"), {"meta": {"motor": "dotnet"}}).run(r"(a+)+$", "a" * 35 + "!")
        self.assertEqual(sinir["error"]["type"], "EşleşmeHatası")
        with self.assertRaises(ValueError):
            runners.for_step(runners.get("sql"), {"meta": {"motor": "dotnet"}})


if __name__ == "__main__":
    unittest.main(verbosity=1)
