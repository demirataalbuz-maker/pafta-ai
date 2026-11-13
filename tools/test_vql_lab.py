# -*- coding: utf-8 -*-
"""Purple yolunun Velociraptor laboratuvarı (sandbox/vql_lab.py, py_harness vql_*).

Velociraptor ikilisi .deps/velociraptor'da yoksa testler atlanır.

    python tools/test_vql_lab.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.runners import for_step, get  # noqa: E402
from sandbox import vql_lab  # noqa: E402

ADIM = {"meta": {"motor": "velociraptor"},
        "setup": ('import os\nos.makedirs("disk/a/B", exist_ok=True)\n'
                  'open("disk/a/B/x.txt", "w").write("merhaba")\nopen("disk/a/y.log", "w").write("")\n')}


def setUpModule():
    sorun = vql_lab.durum()
    if sorun:
        raise unittest.SkipTest(sorun)


class Vql(unittest.TestCase):
    def test_sorgu(self):
        r = for_step(get("purple"), ADIM).run(
            'SELECT relpath(path=OSPath, base=Kok) AS Yol, Size FROM glob(globs="**/*.txt", root=Kok)', "", ADIM["setup"])
        self.assertEqual(r["status"], "ok", r.get("error"))
        self.assertEqual(r["tablolar"][0]["satirlar"], [["a/B/x.txt", "7"]])

    def test_harf_duyarsiz_glob_ve_hata(self):
        r = for_step(get("purple"), ADIM).run('SELECT OSPath.Basename AS Ad FROM glob(globs="A/b/*", root=Kok)', "", ADIM["setup"])
        self.assertEqual(r["tablolar"][0]["satirlar"], [["x.txt"]], "glob desenleri büyük-küçük harfe duyarsız")
        r = for_step(get("purple"), ADIM).run("SELECT FROM", "", ADIM["setup"])
        self.assertEqual(r["status"], "error")
        self.assertIn("VQL", r["error"]["msg"])

    def test_dene(self):
        adim = dict(ADIM, test=("eq(len(sonuc), 2, 'iki')\n"
                                "eq(len(dene('open(\"disk/z.txt\", \"w\").write(\"1\")')), 3, 'dene dosya ekler')"))
        r = for_step(get("purple"), adim).test('SELECT OSPath FROM glob(globs="**/*.*", root=Kok)', adim)
        self.assertEqual(r["status"], "pass", (r.get("checks"), r.get("error")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
