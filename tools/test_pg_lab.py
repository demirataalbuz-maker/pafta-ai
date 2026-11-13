# -*- coding: utf-8 -*-
"""SQL yolunun gerçek PostgreSQL laboratuvarı (motor: postgres) — WSL'deki kümeyle uçtan uca.

    python tools/test_pg_lab.py
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import runners  # noqa: E402
from sandbox import pg_lab  # noqa: E402

HAZIRLIK = """
CREATE TABLE notlar (id serial PRIMARY KEY, metin text NOT NULL, gizli boolean DEFAULT false);
INSERT INTO notlar (metin, gizli) VALUES ('açık not', false), ('gizli not', true);
"""


def adim(test="", setup=HAZIRLIK):
    return {"meta": {"motor": "postgres"}, "setup": setup, "test": test}


def kalintilar():
    kod, out, _ = pg_lab._wsl(["/usr/sbin/runuser", "-u", "postgres", "--", "psql", "-tAc",
                               "SELECT string_agg(rolname, ',') FROM pg_roles WHERE rolname LIKE 'pafta%' OR rolname LIKE 'okuyucu%'"
                               " UNION ALL SELECT string_agg(datname, ',') FROM pg_database WHERE datname LIKE 'pafta%'"], root=True)
    return [s for s in out.split() if s]


class PgLab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pg_lab.available():
            raise unittest.SkipTest("WSL'de PostgreSQL yok")
        cls.r = runners.for_step(runners.get("sql"), adim())

    def test_koşucu_secimi(self):
        self.assertIsInstance(self.r, runners.PostgresRunner)
        with self.assertRaises(ValueError):
            runners.for_step(runners.get("kql"), {"meta": {"motor": "postgres"}})

    def test_calistir_cikti_bicimi(self):
        res = self.r.run("SELECT id, metin, gizli FROM notlar ORDER BY id;\nSELECT NULL::int AS bos, version() LIKE 'PostgreSQL 18%';",
                         "", HAZIRLIK)
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(res["segs"], [["out", "1|açık not|f\n2|gizli not|t\nNULL|t\n"]])

    def test_hata_satiri_ve_kodu(self):
        res = self.r.run("SELECT 1;\nSELECT yok FROM notlar;", "", HAZIRLIK)
        self.assertEqual(res["error"]["type"], "SQLHatası")
        self.assertEqual(res["error"]["line"], 2)
        self.assertEqual(res["error"]["pgcode"], "42703")

    def test_yetki_yardimcilari_ve_temizlik(self):
        kod = ("CREATE ROLE okuyucu NOLOGIN;\n"
               "GRANT SELECT (id, metin) ON notlar TO okuyucu;\n"
               "SELECT has_column_privilege('okuyucu', 'notlar', 'gizli', 'SELECT');")
        test = "\n".join([
            "eq(sonuc, [(False,)], 'gizli sütun okunamaz')",
            "ok(yapabilir('okuyucu', 'SELECT id, metin FROM notlar'), 'izinli sütunlar')",
            "ok(not yapabilir('okuyucu', 'SELECT * FROM notlar'), 'bütün sütunlar değil')",
            "eq(rol_olarak('okuyucu', 'DELETE FROM notlar'), ('hata', '42501'), 'silemez')",
            "eq(rol_olarak('pafta_yonetici', 'DELETE FROM notlar'), ('ok', []), 'yönetici siler')",
            "eq(sorgu('SELECT count(*) FROM notlar'), [(2,)], 'rol_olarak değişikliği geri alındı')",
            "eq(dene('INSERT INTO notlar (metin) VALUES (%s);' % repr('üçüncü')), [(False,)], 'dene temiz veritabanında yeniden kurar')",
            "eq(sorgu('SELECT count(*) FROM notlar'), [(3,)], 'dene hazırlığı uygulandı')",
            "ok(kullanir('grant'), 'kullanir')",
        ])
        res = self.r.test(kod, adim(test))
        self.assertEqual(res["status"], "pass", res)
        self.assertEqual(kalintilar(), [], "iş bitince rol ve veritabanı kalmamalı")

    def test_hazirlik_hatasi(self):
        res = self.r.test("SELECT 1;", adim("ok(True, 'x')", setup="CREATE TABLE ("))
        self.assertEqual(res["status"], "error")
        self.assertIn("hazırlığı", res["error"]["msg"])
        self.assertEqual(kalintilar(), [])

    def test_kapali_kume_yeniden_baslar(self):
        surum, ad = pg_lab.kumeler()[0][:2]
        pg_lab._wsl(["pg_ctlcluster", surum, ad, "stop"], root=True, timeout=90)
        res = self.r.run("SELECT 41 + 1;", "", "")
        self.assertEqual(res["segs"], [["out", "42\n"]], res)


if __name__ == "__main__":
    unittest.main(verbosity=1)
