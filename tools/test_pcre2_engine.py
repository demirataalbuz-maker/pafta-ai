# -*- coding: utf-8 -*-
"""PCRE2 motoru (sandbox/pcre2_engine.py) ve regex yolundaki motor: pcre2 seçeneği.

    python tools/test_pcre2_engine.py
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sandbox"))

import pcre2_engine as p2  # noqa: E402
from engine import runners  # noqa: E402

ORTAK = [  # iki motorda da aynı anlama gelen desenler: sonuçlar birebir aynı olmalı
    (r"\d+", "a1 b22 c333"),
    (r"a*", "baaac"),
    (r"", "abc"),
    (r"\b\w+\b", "Iğdır'da şöyle: çalış, ÖĞRENCİ"),
    (r"(?P<k>\w+)=(?P<v>[^;]*)", "a=1;b=;ç=ş"),
    (r"(a)|(b)", "abc"),
    (r"(?i)pafta", "PAFTA Pafta pafta"),
    (r"x?", "xax"),
    (r"(?<=@)\w+", "ali@ornek ayse@pafta"),
    (r"^\s*#.*$", "kod\n  # yorum\nx"),
]


class Motor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not p2.available():
            raise unittest.SkipTest("PCRE2 kitaplığı yok")

    def test_ortak_desenler_re_ile_ayni(self):
        for desen, metin in ORTAK:
            with self.subTest(desen=desen):
                a, b = re.compile(desen), p2.compile(desen)
                self.assertEqual([(m.span(), m.groups()) for m in a.finditer(metin)],
                                 [(m.span(), m.groups()) for m in b.finditer(metin)])
                self.assertEqual(a.findall(metin), b.findall(metin))
                self.assertEqual(a.split(metin), b.split(metin))

    def test_adli_grup_ve_degistirme(self):
        d = p2.compile(r"(?<y>\d{4})-(?<a>\d{2})")
        self.assertEqual(d.search("tarih 2026-10").groupdict(), {"y": "2026", "a": "10"})
        self.assertEqual(d.sub(r"\g<a>/\g<y>", "2026-10 ve 2025-01"), "10/2026 ve 01/2025")
        self.assertEqual(d.sub(r"\2.\1 \\", "2026-10"), "10.2026 \\")
        self.assertEqual(d.groupindex, {"y": 1, "a": 2})

    def test_turkce_karakter_konumlari(self):
        m = p2.compile(r"ş+").search("aşşb")
        self.assertEqual((m.span(), m.group(0)), ((1, 3), "şş"))

    def test_pcre2e_ozgu_yapilar(self):
        self.assertEqual(p2.compile(r"\((?:[^()]++|(?R))*\)").findall("f(a(b)c) (d"), ["(a(b)c)"])
        bs = p2.compile(r"(?|(\d+)|([a-z]+))")
        self.assertEqual(bs.groups, 1)
        self.assertEqual(bs.findall("ab12"), ["ab", "12"])
        self.assertEqual(p2.compile(r"(?&n)-(?<n>\d+)").search("12-34").group("n"), "34")
        self.assertEqual(p2.compile(r'"[^"]*"(*SKIP)(*FAIL)|\w+').findall('"ab cd" ef "g" h'), ["ef", "h"])

    def test_buyuk_noktali_i_farki(self):
        # Gerçek lehçe farkı: Python re (?i) ile 'İ'yi 'i' sayar, PCRE2 (UCP) saymaz
        self.assertIsNotNone(re.search(r"(?i)istanbul", "İSTANBUL"))
        self.assertIsNone(p2.compile(r"(?i)istanbul").search("İSTANBUL"))

    def test_python_re_bunlari_derlemez(self):
        for desen in (r"(?R)", r"(?|a|b)", r"x(*SKIP)(*F)|y"):
            with self.subTest(desen=desen), self.assertRaises(re.error):
                re.compile(desen)

    def test_derleme_hatasi_konumu(self):
        with self.assertRaises(p2.Pcre2Hatasi) as h:
            p2.compile("ğğ(")
        self.assertIn("parenthesis", h.exception.msg)
        self.assertEqual(h.exception.pos, 3)

    def test_felaket_geri_izleme_sinirda_durur(self):
        with self.assertRaises(p2.Pcre2Hatasi):
            p2.compile(r"(a+)+$").search("a" * 40 + "!")

    def test_fullmatch_match(self):
        d = p2.compile(r"\d+")
        self.assertIsNone(d.fullmatch("12a"))
        self.assertEqual(d.fullmatch("123").group(), "123")
        self.assertIsNone(d.match("a12"))


class Kosucu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not p2.available():
            raise unittest.SkipTest("PCRE2 kitaplığı yok")

    def kos(self, meta):
        return runners.for_step(runners.get("regex"), {"meta": meta})

    def test_motor_secimi(self):
        self.assertIsInstance(self.kos({"motor": "pcre2"}), runners.Pcre2Runner)
        self.assertNotIsInstance(self.kos({}), runners.Pcre2Runner)
        with self.assertRaises(ValueError):
            self.kos({"motor": "perl"})
        with self.assertRaises(ValueError):
            runners.for_step(runners.get("sql"), {"meta": {"motor": "pcre2"}})

    def test_calistir_ve_test(self):
        r = self.kos({"motor": "pcre2"})
        res = r.run(r"\((?:[^()]++|(?R))*\)", "f(a(b)c) g(h)")
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(res["segs"], [["out", "(a(b)c)\n(h)\n"]])
        adim = {"meta": {"motor": "pcre2"}, "test": "eq(bul('a(b(c))d'), ['(b(c))'], 'iç içe')\nok(tam('(x)'), 'tam')"}
        self.assertEqual(r.test(r"\((?:[^()]++|(?R))*\)", adim)["status"], "pass")
        hata = r.run("(", "x")
        self.assertEqual(hata["error"]["type"], "DesenHatası")
        self.assertIn("PCRE2", hata["error"]["msg"])
        self.assertIn("PCRE2", r.dis(r"(?<n>a)")["text"])
        sinir = r.run(r"(a+)+$", "a" * 40 + "!")
        self.assertEqual(sinir["error"]["type"], "EşleşmeHatası")

    def test_python_motoru_ayni_deseni_reddeder(self):
        res = runners.get("regex").run(r"(?R)", "x")
        self.assertEqual(res["error"]["type"], "DesenHatası")


if __name__ == "__main__":
    unittest.main(verbosity=1)
