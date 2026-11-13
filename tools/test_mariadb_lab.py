# -*- coding: utf-8 -*-
"""SQL yolunun gerçek MariaDB laboratuvarı (motor: mariadb) — WSL'deki sunucuyla uçtan uca.

    python tools/test_mariadb_lab.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import runners  # noqa: E402
from sandbox import mariadb_lab, pg_lab  # noqa: E402

HAZIRLIK = "CREATE TABLE notlar (id INT PRIMARY KEY AUTO_INCREMENT, metin VARCHAR(50) NOT NULL);\n" \
           "INSERT INTO notlar (metin) VALUES ('açık'), ('Gizli');"


def adim(test="", setup=HAZIRLIK):
    return {"meta": {"motor": "mariadb"}, "setup": setup, "test": test}


def kalan_veritabanlari():
    _, out, _ = pg_lab._wsl(["mariadb", "-N", "-e", "SHOW DATABASES LIKE 'pafta\\_%'"], root=True)
    return out.split()


class MariadbLab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not mariadb_lab.available():
            raise unittest.SkipTest("WSL'de MariaDB yok")
        cls.r = runners.for_step(runners.get("sql"), adim())

    def test_kosucu_secimi(self):
        self.assertIsInstance(self.r, runners.MariadbRunner)
        with self.assertRaises(ValueError):
            runners.for_step(runners.get("spl"), {"meta": {"motor": "mariadb"}})

    def test_lehce_ve_cikti_bicimi(self):
        res = self.r.run("SELECT 'a' || 'b', CONCAT('a', NULL), 7/2, 7 DIV 2, 'a' = 'A', 0.1 + 0.2;\n"
                         "SELECT metin FROM notlar ORDER BY id;", "", HAZIRLIK)
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(res["segs"], [["out", "0|NULL|3.5000|3|1|0.3\naçık\nGizli\n"]])

    def test_hata_satiri_ve_kodu(self):
        res = self.r.run("SELECT 1;\nSELECT yok FROM notlar;", "", HAZIRLIK)
        self.assertEqual((res["error"]["type"], res["error"]["line"], res["error"]["mycode"]), ("SQLHatası", 2, 1054))

    def test_yardimcilar_ve_temizlik(self):
        test = "\n".join([
            "eq(sonuc, [(2,)], 'iki satır')",
            "eq(sorgu('SELECT metin FROM notlar WHERE id = %s', 2), [('Gizli',)], 'parametreli sorgu')",
            "eq(dene(\"INSERT INTO notlar (metin) VALUES ('üç');\"), [(3,)], 'dene temiz veritabanında yeniden kurar')",
            "eq([u[2] for u in uyarilar], [1292], 'dene uyarıları sıfırlar: yalnız yeniden çalıştırmanın uyarısı kalır')",
        ])
        res = self.r.test("SELECT 'abc' + 1;\nSELECT COUNT(*) FROM notlar;", adim(test))
        self.assertEqual(res["status"], "pass", res)
        self.assertEqual(kalan_veritabanlari(), [], "iş bitince veritabanı kalmamalı")

    def test_uyarilar_testte_gorunur(self):
        res = self.r.test("SELECT 'abc' + 1;", adim("eq([(u[1], u[2]) for u in uyarilar], [('Warning', 1292)], 'çevrilemeyen metin uyarısı')"))
        self.assertEqual(res["status"], "pass", res)

    def test_yetki_yalniz_pafta_veritabanlari(self):
        res = self.r.run("CREATE DATABASE baska;", "", "")
        self.assertEqual(res["error"]["mycode"], 1044, res)

    def test_hazirlik_hatasi(self):
        res = self.r.test("SELECT 1;", adim("ok(True, 'x')", setup="CREATE TABLE ("))
        self.assertEqual(res["status"], "error")
        self.assertIn("hazırlığı", res["error"]["msg"])
        self.assertEqual(kalan_veritabanlari(), [])

    def test_kapali_sunucu_yeniden_baslar(self):
        pg_lab._wsl(["systemctl", "stop", "mariadb"], root=True, timeout=90)
        res = self.r.run("SELECT 41 + 1;", "", "")
        self.assertEqual(res["segs"], [["out", "42\n"]], res)


if __name__ == "__main__":
    unittest.main(verbosity=1)
