"""End-to-end local API checks using disposable progress, never user progress."""
import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server


class DetectionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pafta_detection_test_")
        cls.environment = patch.dict(os.environ, {"PAFTA_DATA": cls.temp.name})
        cls.environment.start()
        cls.app, cls.httpd = server.start(0)
        cls.base = f"http://127.0.0.1:{cls.app.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.environment.stop()
        cls.temp.cleanup()

    def request(self, path, payload=None):
        headers = {"X-Pafta-Token": self.app.token, "Origin": self.base}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    def test_tracks_lessons_grading_prediction_and_progress(self):
        state = self.request("/api/state")
        for tid in ("sigma", "yara"):
            with self.subTest(track=tid):
                info = next(track for track in state["tracks"] if track["id"] == tid)
                self.assertEqual(info["status"], "active")
                self.assertTrue(info["hazir"])
                self.assertEqual(info["lessons_total"], 18)
                outline = self.app.lib.outline(tid)
                lid = outline["order"][0]
                lesson = self.app.lib.lesson(tid, lid)
                self.assertIsNotNone(lesson)
                task_index = next(i for i, step in enumerate(lesson["steps"]) if step["kind"] == "gorev")
                step = lesson["steps"][task_index]
                payload = {"track": tid, "lesson": lid, "step": task_index}
                failed = self.request("/api/check", dict(payload, code=step["starter"]))
                self.assertNotEqual(failed["status"], "pass")
                passed = self.request("/api/check", dict(payload, code=step["solution"]))
                self.assertEqual(passed["status"], "pass", passed)
                prediction_index = next(i for i, item in enumerate(lesson["steps"]) if item["kind"] == "tahmin")
                prediction = lesson["steps"][prediction_index]
                output = self.request("/api/run", {"track": tid, "code": prediction["code"], "stdin": prediction.get("stdin", "")})
                self.assertEqual(output["status"], "ok", output)
                actual = "".join(text for kind, text in output["segs"] if kind == "out")
                guessed = self.request("/api/guess", {"track": tid, "lesson": lid, "step": prediction_index, "guess": actual})
                self.assertTrue(guessed["correct"], guessed)
                saved = json.loads(Path(self.app.prog.path).read_text(encoding="utf-8"))
                self.assertTrue(saved["tracks"][tid]["steps"][f"{lid}:{task_index}"]["done"])
                self.assertIn(f"{lid}:{task_index}", saved["tracks"][tid]["review"])
        self.assertTrue(Path(self.app.prog.path).is_relative_to(Path(self.temp.name)))


if __name__ == "__main__":
    unittest.main()
