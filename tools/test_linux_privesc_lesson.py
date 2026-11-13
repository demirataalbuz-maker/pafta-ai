# -*- coding: utf-8 -*-
"""PU16 fixture güvenliği, doğrudan runner ve yanlış karar mutasyonları."""
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox.linux_privesc_lab import FIXTURE, hazirla, veri_yukle  # noqa: E402

LESSON_PATH = ROOT / "tracks" / "purple" / "lessons" / "pu16-linux-yetki-yukseltme-analizi.md"
TASKS = Library().lesson("purple", "pu16")["steps"]
GOREVLER = [s for s in TASKS if s["kind"] == "gorev"]

# görev, çözümdeki özgün parça, yanlış karşılık, reddedilen karar hatası
MUTATIONS = [
    (0, 'f["kind"] != "regular" or not f["executable"]', 'False', "çalıştırılamayan dosya ve socket"),
    (0, 'if not (f["caller_write"] or f["parent_replace"]):', 'if False:', "SUID varlığını otomatik bulgu sayma"),
    (0, 'f["owner"] != kimlik["user"]', 'True', "aynı kullanıcı SUID sınırı"),
    (0, 'f["group"] not in kimlik["groups"]', 'True', "üye olunan SGID grubu"),
    (0, '{"e", "p"} & set(bayraklar)', 'set(bayraklar)', "yalnız inheritable capability"),
    (0, 'p["namespace"] != "initial"', 'False', "kullanıcı ad alanını ana sistem sayma"),
    (0, 'etkin = "e" in bayraklar', 'etkin = False', "effective capability önceliği"),
    (1, 'principal == kimlik["user"] or (principal.startswith("%") and principal[1:] in kimlik["groups"])', 'True', "başka kullanıcı/grup sudo kuralı"),
    (1, 'if not wildcard:', 'if False:', "sabit sudo argümanı"),
    (1, 'root = "root" in r["runas_users"] or "root" in r["runas_groups"]', 'root = False', "root runas hedefi"),
    (1, 'nopasswd = r["auth"] == "NOPASSWD"', 'nopasswd = False', "parolasız sudo önceliği"),
    (1, 'not r["noexec"]', 'True', "NOEXEC öncelik sınırı"),
    (2, 'if not j["trigger_active"] or j["user"] == kullanici:', 'if False:', "inactive ve aynı kullanıcı işi"),
    (2, 'if j["script"] and (j["caller_script_write"] or j["caller_parent_replace"]):', 'if False:', "betik/üst dizin yazma önkoşulu"),
    (2, 'if not j["command_absolute"]:', 'if False:', "mutlak komutta PATH hijack"),
    (2, 'if p["caller_write"]:', 'if False:', "yazılabilir PATH önkoşulu"),
    (2, 'if not p["absolute"]:', 'if False:', "göreli ve boş PATH"),
    (2, 'yuksek = "kritik" if root else "yuksek"', 'yuksek = "yuksek"', "root zamanlanmış iş önceliği"),
]


class FixtureSafety(unittest.TestCase):
    def test_schema_and_synthetic_scope(self):
        data = veri_yukle()
        self.assertEqual(data["schema_version"], 1)
        self.assertIn("sentetik", data["scenario"])
        self.assertEqual(data["identity"]["user"], "analyst")
        self.assertTrue(data["sudo_rules"])
        self.assertTrue(data["jobs"])
        self.assertTrue(data["file_capabilities"])
        self.assertTrue(data["process_capabilities"])

    def test_helper_only_copies_fixture(self):
        original = FIXTURE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            target = hazirla(tmp)
            self.assertEqual(target.name, "pu16_lab.json")
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["scenario"],
                             veri_yukle()["scenario"])
        self.assertEqual(FIXTURE.read_bytes(), original)

    def test_helper_has_no_process_network_or_privilege_mutation(self):
        tree = ast.parse((ROOT / "sandbox" / "linux_privesc_lab.py").read_text(encoding="utf-8"))
        imported = set()
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
        self.assertTrue(imported <= {"pathlib", "json", "shutil"}, imported)
        self.assertFalse(called & {"run", "Popen", "system", "chmod", "chown", "setuid", "setcap"}, called)

    def test_utf8_lf(self):
        for path in (LESSON_PATH, FIXTURE, FIXTURE.with_name("README.md"),
                     ROOT / "sandbox" / "linux_privesc_lab.py", Path(__file__)):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, path)
            raw.decode("utf-8")


class LessonChecks(unittest.TestCase):
    def sonuc(self, index, code):
        step = GOREVLER[index]
        return for_step(get("purple"), step).test(code, step)

    def gecmeli(self, index, code):
        result = self.sonuc(index, code)
        self.assertEqual(result["status"], "pass", result)

    def kalmali(self, index, code):
        result = self.sonuc(index, code)
        self.assertEqual(result["status"], "fail", result)

    def test_exactly_three_tasks(self):
        self.assertEqual(len(GOREVLER), 3)

    def test_prediction(self):
        step = next(s for s in TASKS if s["kind"] == "tahmin")
        result = for_step(get("purple"), step).run(step["code"], setup=step.get("setup"))
        self.assertEqual(result["status"], "ok", result)
        output = "".join(value for kind, value in result["segs"] if kind == "out")
        self.assertEqual(output, "['/opt/root-report']\n")

    def test_solutions_pass_and_starters_fail(self):
        for index, step in enumerate(GOREVLER):
            with self.subTest(task=index + 1, kind="solution"):
                self.gecmeli(index, step["solution"])
            with self.subTest(task=index + 1, kind="starter"):
                self.kalmali(index, step["starter"])

    def test_wrong_decision_and_priority_mutants_are_rejected(self):
        for index, old, new, name in MUTATIONS:
            step = GOREVLER[index]
            with self.subTest(task=index + 1, mutation=name):
                self.assertIn(old, step["solution"])
                self.kalmali(index, step["solution"].replace(old, new, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
