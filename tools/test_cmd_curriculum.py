"""CMD lesson structure and native prediction consistency checks."""
import re
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import argv_coz, get


class CmdCurriculumTests(unittest.TestCase):
    def setUp(self):
        self.library = Library()
        self.outline = self.library.outline("cmd")

    def test_catalog_source_and_every_lesson_has_native_prediction(self):
        self.assertEqual(self.outline["runner"], "cmd")
        self.assertEqual(self.outline["dil"], "cmd")
        self.assertFalse(self.outline.get("okuma_dili"))
        self.assertEqual(self.outline["order"], [f"cm{i:02}" for i in range(1, 26)])
        self.assertEqual(len(self.outline["ranks"]), 6)
        self.assertEqual({m["rank"] for m in self.outline["modules"]},
                         {r["id"] for r in self.outline["ranks"]})
        for path in (ROOT / "tracks" / "cmd").rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                raw.decode("utf-8")
                self.assertNotIn(b"\r", raw, str(path))
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), str(path))
        for lesson_id in self.outline["order"]:
            lesson = self.library.lesson("cmd", lesson_id)
            self.assertIsNotNone(lesson, lesson_id)
            with self.subTest(lesson=lesson_id):
                self.assertEqual(lesson["id"], lesson_id)
                predictions = [s for s in lesson["steps"] if s["kind"] == "tahmin"]
                self.assertTrue(predictions)
                for prediction in predictions:
                    self.assertTrue(prediction["code"])
                    self.assertNotIn("gercek", prediction)
                    self.assertIn("???", prediction["body"])
                tasks = [s for s in lesson["steps"] if s["kind"] == "gorev"]
                self.assertGreaterEqual(len(tasks), 2)
                for task in tasks:
                    for field in ("solution", "test", "starter", "hints"):
                        self.assertTrue(task[field], (lesson_id, field))

    def test_native_prediction_lines_are_explained(self):
        jobs = [(lid, step) for lid in self.outline["order"]
                for step in self.library.lesson("cmd", lid)["steps"] if step["kind"] == "tahmin"]
        def check(job):
            lid, step = job
            result = get("cmd").run(step["code"], step.get("stdin", ""), step.get("setup"),
                                    argv=argv_coz(step.get("meta")))
            return lid, step, result
        with ThreadPoolExecutor(max_workers=4) as pool:
            for lid, step, result in pool.map(check, jobs):
                with self.subTest(lesson=lid):
                    self.assertEqual(result["status"], "ok", result)
                    self.assertFalse(result.get("error"))
                    output = "".join(t for k, t in result.get("segs", []) if k == "out")
                    self.assertTrue(output.strip(), "Prediction must have observable output")
                    explanation = step["body"].split("???", 1)[1]
                    # Ignore Markdown code markers; retain spaces inside values.
                    plain = re.sub(r"[`*]", "", explanation)
                    for line in output.splitlines():
                        if line.strip():
                            self.assertIn(line.strip(), plain, (lid, line, explanation))


if __name__ == "__main__":
    unittest.main(verbosity=2)
