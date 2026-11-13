# -*- coding: utf-8 -*-
"""PU15 sentetik Windows adli izleri dersinin sözleşme/davranış testleri.

    python tools/test_windows_forensics_lesson.py

Ham kanıt, canlı Registry/MFT, ağ, alt süreç veya paket kurulumu kullanılmaz.
"""
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sandbox"))

from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox import windows_forensics_lab as lab  # noqa: E402

LESSON_PATH = ROOT / "tracks/purple/lessons/pu15-windows-adli-izler.md"
TASKS = Library().lesson("purple", "pu15")["steps"]
MUTATIONS = [
    (0, '"last_write_utc": zaman(r["last_write_time"])', '"last_write_utc": r["last_write_time"]',
     "Registry offset UTC'ye çevrilmez"),
    (0, '"son_calistirma_utc": max(zamanlar)', '"son_calistirma_utc": zamanlar[0]',
     "ilk saklanan zaman en yeni sanılır"),
    (0, '"run_count": int(r["run_count"])', '"run_count": len(zamanlar)',
     "run count saklanan zaman sayısından türetilir"),
    (0, 'if r["file_name"].lower() != beklenen.lower():', 'if False:',
     "Prefetch ad/hash uyuşmazlığı yok sayılır"),
    (1, '"data_depo": "resident" if r["data_resident"] else "nonresident"',
     '"data_depo": "nonresident" if r["data_resident"] else "resident"',
     "resident/nonresident terslenir"),
    (1, 'return {harf: zaman(row[alan]) for harf, alan in MACB}',
     'return {harf: row[alan] for harf, alan in MACB}', "MFT zamanları UTC normalize edilmez"),
    (1, 'if si[harf] != fn[harf]', 'if False', "SI/FN farkları silinir"),
    (1, '"hedef_zamanlari_utc": {h: zaman(hedef[a]) for h, a in (("m", "modified"), ("a", "accessed"), ("b", "birth"))}',
     '"hedef_zamanlari_utc": {h: zaman(hedef["modified"] if h == "b" else hedef[a]) for h, a in (("m", "modified"), ("a", "accessed"), ("b", "birth"))}',
     "LNK hedef Birth zamanı Modified ile değiştirilir"),
    (2, 'if p["son_calistirma_utc"] < m["si"]["b"]:', 'if False:',
     "Prefetch/MFT zaman çelişkisi kaybolur"),
    (2, 'if ayni_yol(l["hedef"], m["yol"]) and l["hedef_zamanlari_utc"]["b"] != m["si"]["b"]:',
     'if ayni_yol(l["hedef"], m["yol"]) and False:', "LNK/MFT Birth farkı kaybolur"),
    (2, 'for harf, z in l["dis_zamanlar_utc"].items():', 'for harf, z in {}.items():',
     "LNK dış zamanları zaman çizelgesinden silinir"),
]


class FixtureSozlesmesi(unittest.TestCase):
    def test_kopyalama_kucuk_sentetik_ve_utf8_lf(self):
        with tempfile.TemporaryDirectory(prefix="pu15_test_") as tmp:
            hedef = lab.hazirla(tmp)
            self.assertEqual(hedef.name, "adli")
            self.assertEqual({p.name for p in hedef.iterdir()}, set(lab.DOSYALAR))
            for ad in lab.DOSYALAR:
                kaynak = lab.FIXTURE / ad
                self.assertEqual((hedef / ad).read_bytes(), kaynak.read_bytes())
                raw = kaynak.read_bytes()
                self.assertNotIn(b"\r", raw, str(kaynak))
                raw.decode("utf-8")
                self.assertLess(len(raw), 4096, str(kaynak))
        for path in (LESSON_PATH, Path(__file__), ROOT / "sandbox/windows_forensics_lab.py"):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, str(path))
            raw.decode("utf-8")

    def test_normalize_fixture_gercek_ham_kanit_degildir(self):
        for ad in lab.DOSYALAR:
            self.assertTrue(ad.endswith((".json", ".md")))
        veri = {ad: json.loads((lab.FIXTURE / ad).read_text(encoding="utf-8"))
                for ad in lab.DOSYALAR if ad.endswith(".json")}
        self.assertEqual(len(veri["registry.json"]), 2)
        self.assertEqual(veri["prefetch.json"][0]["run_count"], 7)
        self.assertEqual(len(veri["prefetch.json"][0]["last_run_times"]), 2)
        self.assertFalse(veri["mft.json"][0]["data_resident"])
        self.assertTrue(veri["mft.json"][1]["data_resident"])
        self.assertNotEqual(veri["mft.json"][0]["standard_information"]["birth"],
                            veri["mft.json"][0]["file_name"]["birth"])
        self.assertNotEqual(veri["lnk.json"][0]["target_times"]["birth"],
                            veri["mft.json"][0]["standard_information"]["birth"])
        self.assertIn("sentetik", (lab.FIXTURE / "README.md").read_text(encoding="utf-8").lower())

    def test_yardimci_canli_sistem_ve_alt_surec_ice_aktarmaz(self):
        tree = ast.parse((ROOT / "sandbox/windows_forensics_lab.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {"datetime", "json", "pathlib", "shutil"}, imported)
        self.assertNotIn("winreg", imported)
        self.assertNotIn("subprocess", imported)

    def test_zaman_dilimsiz_degeri_tahmin_etmez(self):
        self.assertEqual(lab.zaman("2026-10-20T11:20:00+03:00"), "2026-10-20 08:20:00")
        self.assertEqual(lab.zaman("2026-10-20T08:20:00Z"), "2026-10-20 08:20:00")
        with self.assertRaisesRegex(ValueError, "Saat dilimi gerekli"):
            lab.zaman("2026-10-20 08:20:00")


class DersDavranisi(unittest.TestCase):
    def test_anlat_tahmin_gorev_yapisi(self):
        kinds = [s["kind"] for s in TASKS]
        self.assertEqual(kinds.count("tahmin"), 1)
        self.assertEqual(kinds.count("gorev"), 3)
        self.assertGreaterEqual(kinds.count("anlat"), 4)
        metin = LESSON_PATH.read_text(encoding="utf-8")
        for kavram in ("LastWriteTime", "run_count", "$STANDARD_INFORMATION", "$FILE_NAME",
                       "resident", "nonresident", "MACB", "Modified", "Accessed", "Changed", "Birth",
                       "çalışma dizini", "UTC", "timestomp"):
            self.assertIn(kavram, metin)

    def test_tahmin_ciktisi(self):
        step = next(s for s in TASKS if s["kind"] == "tahmin")
        result = for_step(get("purple"), step).run(step["code"], setup=step.get("setup"))
        self.assertEqual(result["status"], "ok", result)
        output = "".join(value for kind, value in result["segs"] if kind == "out")
        self.assertEqual(output, "['2026-10-20 08:12:00', '2026-10-20 08:20:00']\n2026-10-20 08:20:00\n")

    def test_solution_kabul_starter_red(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        self.assertEqual(len(tasks), 3)
        for index, step in enumerate(tasks):
            with self.subTest(task=index, code="solution"):
                result = for_step(get("purple"), step).test(step["solution"], step)
                self.assertEqual(result["status"], "pass", result)
            with self.subTest(task=index, code="starter"):
                result = for_step(get("purple"), step).test(step["starter"], step)
                self.assertEqual(result["status"], "fail", result)

    def test_yanlis_zaman_ve_yorumlar_davranissal_yakalanir(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        for index, old, new, name in MUTATIONS:
            step = tasks[index]
            with self.subTest(task=index, mutation=name):
                self.assertIn(old, step["solution"])
                result = for_step(get("purple"), step).test(step["solution"].replace(old, new, 1), step)
                self.assertEqual(result["status"], "fail", result)

    def test_celiski_kaynaklari_tek_olaya_birlestirilmez(self):
        task = [s for s in TASKS if s["kind"] == "gorev"][2]
        module = ast.parse(task["solution"])
        module.body = [n for n in module.body if isinstance(n, (ast.FunctionDef, ast.Assign))
                       and (not isinstance(n, ast.Assign)
                            or any(isinstance(t, ast.Name) and t.id == "MACB" for t in n.targets))]
        ns = {"__name__": "pu15_test", "zaman": lab.zaman}
        exec(compile(module, "<pu15-celiski>", "exec"), ns)
        rs = ns["registry_izleri"](json.loads((lab.FIXTURE / "registry.json").read_text(encoding="utf-8")))
        ps = ns["prefetch_izleri"](json.loads((lab.FIXTURE / "prefetch.json").read_text(encoding="utf-8")))
        ms = ns["mft_izleri"](json.loads((lab.FIXTURE / "mft.json").read_text(encoding="utf-8")))
        ls = ns["lnk_izleri"](json.loads((lab.FIXTURE / "lnk.json").read_text(encoding="utf-8")))
        before = copy.deepcopy((rs, ps, ms, ls))
        rapor = ns["zaman_raporu"](rs, ps, ms, ls)
        self.assertEqual(len(rapor["olaylar"]), 25)
        self.assertEqual([c["kod"] for c in rapor["celiskiler"]],
                         ["calistirma-si-dogum-oncesi", "lnk-mft-dogum-farki"])
        zamanlar = {o["zaman"] for o in rapor["olaylar"]}
        for c in rapor["celiskiler"]:
            self.assertTrue(set(c["zamanlar"].values()) <= zamanlar)
            self.assertEqual(len(c["kaynaklar"]), 2)
        self.assertEqual((rs, ps, ms, ls), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
