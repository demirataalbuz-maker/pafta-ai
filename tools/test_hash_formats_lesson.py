# -*- coding: utf-8 -*-
"""PU17 parola özeti biçimleri dersi; yalnız çevrimdışı parser/test vektörleri.

    python tools/test_hash_formats_lesson.py
"""
import ast
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sandbox"))

from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox import hash_formats_lab as lab  # noqa: E402

LESSON_PATH = ROOT / "tracks/purple/lessons/pu17-parola-ozeti-bicimleri.md"
TASKS = Library().lesson("purple", "pu17")["steps"]
MUTATIONS = [
    (0, r"(0[4-9]|[12][0-9]|3[01])", r"([0-9]+)", "bcrypt cost aralığı yok sayılır"),
    (0, "if not 1000 <= rounds <= 999999999:", "if False:", "sha512crypt rounds aralığı yok sayılır"),
    (0, '([./A-Za-z0-9]{22})([./A-Za-z0-9]{31})', '([./A-Za-z0-9]+)([./A-Za-z0-9]+)', "bcrypt salt/digest sınırları kaldırılır"),
    (0, 'raise ValueError("Desteklenmeyen veya belirsiz özet biçimi")', 'return {"tur":"bilinmiyor", "digest":metin}', "belirsiz biçim kabul edilir"),
    (1, 'alanlar = satir.rstrip("\\n").split(":")', 'alanlar = (satir.rstrip("\\n").split(":") + [""] * 9)[:9]', "eksik shadow alanları doldurulup kabul edilir"),
    (1, 'if len(kullanicilar) > 1', 'if len(kullanicilar) > 99', "salt tekrarı raporlanmaz"),
    (1, 'kayit["ozet"]["cost"] < minimum_bcrypt_cost', 'kayit["ozet"]["cost"] > minimum_bcrypt_cost', "bcrypt cost karşılaştırması terslenir"),
    (1, 'kayit["ozet"]["tur"] == "bcrypt"', 'kayit["ozet"]["tur"] == "yescrypt" and "cost" in kayit["ozet"]', "bcrypt cost kontrolü yanlış türe kayar"),
    (2, '"yescrypt":"30600"', '"yescrypt":"1800"', "yescrypt ve sha512crypt Hashcat modları karışır"),
    (2, '"ntlm":"nt"', '"ntlm":"1000"', "John ve Hashcat modları karışır"),
    (2, "arac_modu(arac, tur)\n    return True", "return False", "sürüm doğrulama yükümlülüğü kaldırılır"),
]


class LaboratuvarVeFixture(unittest.TestCase):
    def test_md4_rfc_ve_ntlm_vektorleri(self):
        vektorler = {
            b"": "31d6cfe0d16ae931b73c59d7e0c089c0",
            b"a": "bde52cb31de33e46245e05fbdbd6fb24",
            b"abc": "a448017aaf21d8525fc10ae87aa6729d",
            b"message digest": "d9130a8164549fe818874806e1c7014b",
            b"12345678901234567890123456789012345678901234567890123456789012345678901234567890": "e33b4ddc9c38f2199c3e7b164fcc0536",
        }
        for veri, beklenen in vektorler.items():
            with self.subTest(veri=veri):
                self.assertEqual(lab.md4(veri), beklenen)
        self.assertEqual(lab.ntlm_test_ozeti("password"), "8846f7eaee8fb117ad06bdd830b7586c")
        self.assertNotEqual(lab.ntlm_test_ozeti("password"), lab.md4(b"password"))

    def test_fixture_kopyalama_ve_vektor_kimlikleri(self):
        with tempfile.TemporaryDirectory(prefix="pu17_test_") as tmp:
            hedef = lab.hazirla(tmp)
            self.assertEqual({p.name for p in hedef.iterdir()}, set(lab.DOSYALAR))
            for ad in lab.DOSYALAR:
                self.assertEqual((hedef / ad).read_bytes(), (lab.FIXTURE / ad).read_bytes())
        veri = lab.json_yukle(lab.FIXTURE / "hashes.json")
        self.assertIn("sentetik", veri["senaryo"])
        self.assertEqual(len(veri["kayitlar"]), 6)
        self.assertEqual(veri["kayitlar"][0]["hash"], lab.ntlm_test_ozeti("password"))
        shadow = (lab.FIXTURE / "shadow.txt").read_text(encoding="utf-8").splitlines()
        self.assertTrue(all(len(satir.split(":")) == 9 for satir in shadow))
        self.assertNotIn("$2b$12$SALT$", "\n".join(shadow), "uydurma digest fixture'a girmemeli")

    def test_yardimci_guvenli_ice_aktarmalar(self):
        tree = ast.parse((ROOT / "sandbox/hash_formats_lab.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {"pathlib", "json", "shutil", "struct"}, imported)

    def test_utf8_lf(self):
        for path in [LESSON_PATH, Path(__file__), ROOT / "sandbox/hash_formats_lab.py",
                     *(lab.FIXTURE / ad for ad in lab.DOSYALAR)]:
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, str(path))
            raw.decode("utf-8")


class DersDavranisi(unittest.TestCase):
    def test_tahmin_ciktisi(self):
        step = next(s for s in TASKS if s["kind"] == "tahmin")
        result = for_step(get("purple"), step).run(step["code"], setup=step.get("setup"))
        self.assertEqual(result["status"], "ok", result)
        output = "".join(value for kind, value in result["segs"] if kind == "out")
        self.assertEqual(output, "a448017aaf21d8525fc10ae87aa6729d\n8846f7eaee8fb117ad06bdd830b7586c\nFalse\n")

    def test_solution_kabul_starter_red(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        self.assertEqual(len(tasks), 5)
        for index, step in enumerate(tasks):
            with self.subTest(task=index, code="solution"):
                result = for_step(get("purple"), step).test(step["solution"], step)
                self.assertEqual(result["status"], "pass", result)
            with self.subTest(task=index, code="starter"):
                result = for_step(get("purple"), step).test(step["starter"], step)
                self.assertEqual(result["status"], "fail", result)

    def test_yanlis_cozumler_mutasyonla_reddedilir(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        for index, old, new, name in MUTATIONS:
            step = tasks[index]
            with self.subTest(task=index, mutation=name):
                self.assertIn(old, step["solution"])
                result = for_step(get("purple"), step).test(step["solution"].replace(old, new, 1), step)
                self.assertEqual(result["status"], "fail", result)

    def test_bes_gorev_ve_kapsam(self):
        kinds = [s["kind"] for s in TASKS]
        self.assertEqual(kinds.count("gorev"), 5)
        self.assertIn("anlat", kinds)
        self.assertIn("tahmin", kinds)
        metin = LESSON_PATH.read_text(encoding="utf-8")
        for kavram in ("MD4(UTF-16LE)", "$2a$", "$2b$", "$2y$", "$6$", "$y$",
                       "salt", "work factor", "1000", "3200", "1800", "30600",
                       "sürüme ve derlemeye", "güvenli saklama"):
            self.assertIn(kavram, metin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
