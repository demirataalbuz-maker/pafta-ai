"""PU06 sentetik fixture güvenliği, görev sınırları ve mutasyon kontrolleri."""
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get
from sandbox.attack_analysis_lab import FIXTURE, hazirla, veri_yukle

LESSON_PATH = ROOT / "tracks/purple/lessons/pu12-saldiri-zinciri-analizi.md"
TASKS = Library().lesson("purple", "pu12")["steps"]

# (görev sırası, çözümdeki özgün parça, bozuk karşılığı, kontrolün amacı)
MUTATIONS = [
    (0, '{"e", "p"} & set(bayraklar)', 'set(bayraklar)', "yalnız inheritable capability"),
    (0, 'kayit["runas"] == "root"', 'True', "root olmayan sudo hedefi"),
    (0, 'kayit["nopasswd"]', 'True', "parola gerektiren sudo"),
    (0, '"*" in kayit["command"]', 'True', "sabit sudo komutu"),
    (0, 'kayit["owner"] != "root"', 'False', "root dışı cron sahibi"),
    (0, 'not dizin.startswith("/")', 'False', "göreli ve boş PATH"),
    (0, 'return sorted(bulgular)', 'return []', "Linux bulgularının kaybı"),
    (1, 'grup["enabled"] and not grup["deny_only"]', 'True', "deny-only grup"),
    (1, 'ace["type"] == "deny"', 'False', "deny ACE önceliği"),
    (1, 'ace["sid"] in sidler', 'True', "tam ve etkin SID eşleşmesi"),
    (1, 'if not oturum["run_as_virtual_account"]:', 'if False:', "JEA sanal hesap bağlamı"),
    (1, 'if len(yol) < 3 or not (yol[0].isalpha() and yol[1:3] == ":\\\\"):', 'if False:', "JEA tam dış komut yolu"),
    (1, 'if komut.lower() in fn["body"].lower():', 'if False:', "JEA fonksiyon gövdesi"),
    (2, 'o["event_id"] in (4625, 4771)', 'o["event_id"] == 4625', "4771 başarısızlığı"),
    (2, 'o["status"] != "0x0"', 'False', "4776 durum ayrımı"),
    (2, 'len(kayitlar) < esik', 'len(kayitlar) <= esik', "eşik sınırı"),
    (2, 'max(sayim.values()) < esik', 'True', "püskürtme ve karma ayrımı"),
    (2, 'len(sayim) == 1', 'False', "tek hesaba kaba kuvvet"),
    (2, 'anahtar = (o["source_ip"], o["account"])', 'anahtar = (o["source_ip"],)', "kaynak ve hesap eşleşmesi"),
    (2, '<= pencere]', '< pencere]', "pencere üst sınırı"),
    (3, 'o["logon_type"] not in (3, 10)', 'False', "Logon Type süzgeci"),
    (3, 'kaynak not in kapsam', 'False', "kaynak kapsam koşulu"),
    (3, 'hedef in kapsam', 'False', "yinelenen hedef"),
    (3, 'o["time"] < baslangic_zamani', 'False', "başlangıç zamanı"),
    (3, 'kapsam.add(hedef)', 'pass', "zincirin yeni hedefle büyümesi"),
]


class FixtureSafety(unittest.TestCase):
    def test_ids_and_synthetic_scope(self):
        data = veri_yukle()
        self.assertIn("sentetik", data["senaryo"])
        self.assertEqual({o["event_id"] for o in data["ad_events"]},
                         {4624, 4625, 4768, 4769, 4771, 4776})
        self.assertEqual({o["logon_type"] for o in data["ad_events"] if o["event_id"] == 4624},
                         {2, 3, 10})
        forbidden = {"password", "passwd", "hash", "nthash", "ticket", "krbtgt", "secret"}
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key.lower(), forbidden)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(data)

    def test_helper_only_copies_fixture(self):
        original = FIXTURE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            target = hazirla(tmp)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["senaryo"],
                             veri_yukle()["senaryo"])
        self.assertEqual(FIXTURE.read_bytes(), original)

    def test_helper_has_no_process_or_network_execution(self):
        tree = ast.parse((ROOT / "sandbox/attack_analysis_lab.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {"pathlib", "json", "shutil"}, imported)

    def test_utf8_lf(self):
        for path in (LESSON_PATH, FIXTURE, FIXTURE.with_name("README.md"),
                     ROOT / "sandbox/attack_analysis_lab.py", Path(__file__)):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, path)
            raw.decode("utf-8")


class LessonChecks(unittest.TestCase):
    def test_prediction(self):
        step = next(s for s in TASKS if s["kind"] == "tahmin")
        result = for_step(get("purple"), step).run(step["code"], setup=step.get("setup"))
        self.assertEqual(result["status"], "ok", result)
        output = "".join(value for kind, value in result["segs"] if kind == "out")
        self.assertEqual(output, "4768 ayse PC-AYSE DC01\n4769 ayse SRV-PORTAL DC01\n")

    def test_solution_passes_and_starter_fails(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        self.assertEqual(len(tasks), 4)
        for index, step in enumerate(tasks):
            with self.subTest(task=index, kind="solution"):
                result = for_step(get("purple"), step).test(step["solution"], step)
                self.assertEqual(result["status"], "pass", result)
            with self.subTest(task=index, kind="starter"):
                result = for_step(get("purple"), step).test(step["starter"], step)
                self.assertEqual(result["status"], "fail", result)

    def test_mutants_are_rejected(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        for index, old, new, name in MUTATIONS:
            step = tasks[index]
            with self.subTest(task=index, mutation=name):
                self.assertIn(old, step["solution"])
                result = for_step(get("purple"), step).test(step["solution"].replace(old, new, 1), step)
                self.assertEqual(result["status"], "fail", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
