"""HTTP API executes student queries and keeps solutions/corpora authoritative."""
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


class ElasticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pafta_elastic_test_")
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
        with urllib.request.urlopen(req, timeout=100) as response:
            return json.load(response)

    def test_catalog_and_languages(self):
        state = self.request("/api/state")
        info = next(t for t in state["tracks"] if t["id"] == "elastic")
        self.assertTrue(info["hazir"])
        self.assertEqual(info["lessons_total"], 27)
        self.assertEqual(info["dil"], "elastic")
        self.assertIsNone(info.get("okuma_dili"))
        self.assertIn("Kusto", next(t for t in state["tracks"] if t["id"] == "kql")["name"])
        for lid, language in (("el01", "kibana"), ("el07", "lucene"), ("el13", "eql")):
            view = self.request(f"/api/lesson/elastic/{lid}")
            self.assertIsNone(view["track"].get("okuma_dili"))
            prediction = next(s for s in view["lesson"]["steps"] if s["kind"] == "tahmin")
            self.assertEqual(prediction["code_dil"], language)
            for step in view["lesson"]["steps"]:
                self.assertFalse({"gercek", "test", "solution", "setup"} & step.keys())

    def test_guesses_invoke_runtime_and_ignore_forged_corpus(self):
        for lid in ("el01", "el07", "el13", "el18", "el19"):
            lesson = self.app.lib.lesson("elastic", lid)
            index = next(i for i, s in enumerate(lesson["steps"]) if s["kind"] == "tahmin")
            step = lesson["steps"][index]
            runner = self.app.runner_for("elastic")
            result = runner.run(step["code"], step["stdin"])
            self.assertEqual(result["status"], "ok", result)
            expected = "".join(t for k, t in result["segs"] if k == "out")
            payload = {"track": "elastic", "lesson": lid, "step": index, "stdin": "{}"}
            with patch.object(runner, "run", wraps=runner.run) as spy:
                wrong = self.request("/api/guess", dict(payload, guess="__wrong__"))
                right = self.request("/api/guess", dict(payload, guess=expected))
                self.assertEqual(spy.call_count, 2)
                self.assertEqual(spy.call_args.args[1], step["stdin"])
            self.assertFalse(wrong["correct"])
            self.assertTrue(right["correct"], right)

    def test_query_grading_run_and_progress_isolation(self):
        lesson = self.app.lib.lesson("elastic", "el01")
        index = next(i for i, s in enumerate(lesson["steps"]) if s["kind"] == "gorev")
        task = lesson["steps"][index]
        payload = {"track": "elastic", "lesson": "el01", "step": index, "stdin": "{}"}
        self.assertNotEqual(self.request("/api/check", dict(payload, code=task["starter"]))["status"], "pass")
        passed = self.request("/api/check", dict(payload, code=task["solution"]))
        self.assertEqual(passed["status"], "pass", passed)
        run = self.request("/api/run", {"track": "elastic", "code": task["solution"], "stdin": task["stdin"]})
        self.assertEqual(run["status"], "ok", run)
        invalid = self.request("/api/run", {"track": "elastic", "code": "print(42)", "stdin": task["stdin"]})
        self.assertEqual(invalid["status"], "error", invalid)
        saved_path = Path(self.app.prog.path)
        self.assertTrue(saved_path.is_relative_to(Path(self.temp.name)))
        saved = json.loads(saved_path.read_text(encoding="utf-8"))["tracks"]["elastic"]
        self.assertTrue(saved["steps"][f"el01:{index}"]["done"])
        self.assertIn(f"el01:{index}", saved["review"])

    def test_native_ingest_rule_esql_through_app(self):
        for lid in ("el20", "el24", "el26"):
            with self.subTest(lesson=lid):
                lesson = self.app.lib.lesson("elastic", lid)
                view = self.request(f"/api/lesson/elastic/{lid}")
                self.assertFalse(any("solution" in step or "test" in step for step in view["lesson"]["steps"]))
                index = next(i for i, step in enumerate(lesson["steps"]) if step["kind"] == "tahmin")
                step = lesson["steps"][index]
                result = self.app.runner_for("elastic").run(step["code"], step["stdin"])
                self.assertEqual(result["status"], "ok", result)
                expected = "".join(t for k, t in result["segs"] if k == "out")
                guessed = self.request("/api/guess", {"track":"elastic", "lesson":lid, "step":index,
                                                      "guess":expected, "stdin":"{}"})
                self.assertTrue(guessed["correct"], guessed)
                index = next(i for i, step in enumerate(lesson["steps"]) if step["kind"] == "gorev")
                task = lesson["steps"][index]
                checked = self.request("/api/check", {"track":"elastic", "lesson":lid, "step":index,
                                                       "code":task["solution"], "stdin":"{}"})
                self.assertEqual(checked["status"], "pass", checked)
                saved = json.loads(Path(self.app.prog.path).read_text(encoding="utf-8"))["tracks"]["elastic"]
                self.assertTrue(saved["steps"][f"{lid}:{index}"]["done"])
                self.assertIn(f"{lid}:{index}", saved["review"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
