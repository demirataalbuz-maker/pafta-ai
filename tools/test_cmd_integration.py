"""CMD local HTTP API test; writes only disposable progress."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server
from engine.runners import argv_coz


class CmdIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pafta_cmd_api_")
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
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)

    def test_real_run_prediction_grading_and_review(self):
        state = self.request("/api/state")
        info = next(t for t in state["tracks"] if t["id"] == "cmd")
        self.assertTrue(info["hazir"])
        self.assertEqual(info["dil"], "cmd")
        self.assertEqual(info["lessons_total"], 24)
        self.assertFalse(info["okuma_dili"])
        self.assertFalse(info["ozellik"]["roentgen"])
        run = self.request("/api/run", {"track": "cmd", "code": '@echo off\nset /a "n=7*6"\necho %n%\n'})
        self.assertEqual(run["status"], "ok", run)
        self.assertEqual("".join(t for k, t in run["segs"] if k == "out"), "42\n")
        lesson = self.app.lib.lesson("cmd", "cm01")
        index = next(i for i, s in enumerate(lesson["steps"]) if s["kind"] == "tahmin")
        step = lesson["steps"][index]
        result = self.app.runner_for("cmd").run(step["code"], step.get("stdin", ""), step.get("setup"),
                                                argv=argv_coz(step.get("meta")))
        actual = "".join(t for k, t in result["segs"] if k == "out")
        guessed = self.request("/api/guess", {"track": "cmd", "lesson": "cm01", "step": index, "guess": actual})
        self.assertTrue(guessed["correct"], guessed)
        self.assertEqual(guessed["result"]["status"], "ok")
        index = next(i for i, s in enumerate(lesson["steps"]) if s["kind"] == "gorev")
        task = lesson["steps"][index]
        payload = {"track": "cmd", "lesson": "cm01", "step": index}
        failed = self.request("/api/check", dict(payload, code=task["starter"]))
        self.assertNotEqual(failed["status"], "pass")
        passed = self.request("/api/check", dict(payload, code=task["solution"]))
        self.assertEqual(passed["status"], "pass", passed)
        saved = json.loads(Path(self.app.prog.path).read_text(encoding="utf-8"))
        self.assertTrue(Path(self.app.prog.path).is_relative_to(Path(self.temp.name)))
        track = saved["tracks"]["cmd"]
        self.assertTrue(track["steps"][f"cm01:{index}"]["done"])
        self.assertIn(f"cm01:{index}", track["review"])
        public = self.request("/api/lesson/cmd/cm01")
        for item in public["lesson"]["steps"]:
            self.assertFalse({"solution", "test", "setup", "gercek"} & item.keys())

    def test_prediction_api_passes_the_declared_arguments(self):
        lesson = self.app.lib.lesson("cmd", "cm03")
        index = next(i for i, s in enumerate(lesson["steps"]) if s["kind"] == "tahmin")
        step = lesson["steps"][index]
        self.assertEqual(argv_coz(step["meta"]), ["web sunucusu", "443"])
        guessed = self.request("/api/guess", {"track": "cmd", "lesson": "cm03", "step": index,
                                              "guess": '"ilk=web sunucusu"\n"yeni-ilk=443"'})
        self.assertTrue(guessed["correct"], guessed)
        view = self.request("/api/lesson/cmd/cm03")
        self.assertEqual(view["lesson"]["steps"][index]["meta"]["argv"], step["meta"]["argv"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
