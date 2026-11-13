"""Writing track contract: real queries, no hand-authored prediction bypass."""
import json
import re
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.lessons import Library, public_step
from engine.runners import get


class ElasticCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = Library()
        cls.outline = cls.library.outline("elastic")

    def test_catalog_and_source_contract(self):
        self.assertEqual(self.outline["runner"], "elastic")
        self.assertEqual(self.outline["dil"], "elastic")
        self.assertNotIn("okuma_dili", self.outline)
        self.assertEqual(self.outline["order"], [f"el{i:02}" for i in range(1, 28)])
        self.assertEqual({m["rank"] for m in self.outline["modules"]}, {r["id"] for r in self.outline["ranks"]})
        self.assertEqual(len(self.outline["modules"]), 6)
        for path in (ROOT / "tracks" / "elastic").rglob("*"):
            if path.is_file():
                data = path.read_bytes()
                self.assertNotIn(b"\r", data, str(path))
                self.assertFalse(data.startswith(b"\xef\xbb\xbf"), str(path))
                data.decode("utf-8")
        for lesson_id in self.outline["order"]:
            lesson = self.library.lesson("elastic", lesson_id)
            self.assertEqual(lesson["id"], lesson_id)
            predictions = [s for s in lesson["steps"] if s["kind"] == "tahmin"]
            self.assertTrue(predictions, lesson_id)
            self.assertGreaterEqual(len([s for s in lesson["steps"] if s["kind"] == "gorev"]), 2)
            for step in lesson["steps"]:
                if step["kind"] not in ("tahmin", "gorev"):
                    continue
                config = json.loads(step["stdin"])
                self.assertEqual(config["dil"], step["meta"]["dil"])
                self.assertIn(config["dil"], ("kibana", "lucene", "eql", "esql", "ingest", "rule"))
                self.assertIsInstance(config["mapping"], dict)
                self.assertTrue(config["documents"])
                if step["kind"] == "tahmin":
                    self.assertEqual(step["code_dil"], config["dil"])
                    self.assertNotIn("gercek", step)
                    self.assertNotIn("test", step)
                    self.assertIn("???", step["body"])
                else:
                    for key in ("test", "solution", "starter", "hints"):
                        self.assertTrue(step[key], (lesson_id, key))
                self.assertFalse({"gercek", "test", "solution", "setup"} & public_step(step).keys())

    def test_prediction_outputs_match_explanations(self):
        jobs = [(lid, step) for lid in self.outline["order"] for step in self.library.lesson("elastic", lid)["steps"] if step["kind"] == "tahmin"]
        def check(job):
            lid, step = job
            return lid, step, get("elastic").run(step["code"], step["stdin"])
        with ThreadPoolExecutor(max_workers=4) as pool:
            for lid, step, result in pool.map(check, jobs):
                with self.subTest(lesson=lid):
                    self.assertEqual(result["status"], "ok", result)
                    output = "".join(text for kind, text in result["segs"] if kind == "out").strip()
                    blocks = re.findall(r"```(?:text|cikti)\s*\n(.*?)```", step["body"], re.S)
                    self.assertIn(output, [b.strip() for b in blocks], (lid, output, blocks))

    def test_solutions_pass_and_starters_do_not(self):
        jobs = [(lid, i, step) for lid in self.outline["order"] for i, step in enumerate(self.library.lesson("elastic", lid)["steps"]) if step["kind"] == "gorev"]
        def check(job):
            lid, i, step = job
            runner = get("elastic")
            return lid, i, runner.test(step["solution"], step), runner.test(step["starter"], step)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for lid, index, solution, starter in pool.map(check, jobs):
                with self.subTest(lesson=lid, step=index):
                    self.assertEqual(solution["status"], "pass", solution)
                    self.assertNotEqual(starter["status"], "pass", starter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
