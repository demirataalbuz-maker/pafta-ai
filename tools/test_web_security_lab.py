"""PU05 native lab, lesson contracts and behavioral wrong-answer tests.

    python -X utf8 tools/test_web_security_lab.py

Only loopback and synthetic data. Browser acceptance is separately opt-in:
    PAFTA_WEB_BROWSER=1 python -X utf8 tools/test_web_security_lab.py BrowserXSS
Nothing is downloaded and command-planning tests never execute a command.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "sandbox")]
from engine.lessons import parse_lesson
from engine.runners import get
from web_security_lab import (CANARY, COMMAND_PLANS, DOMModel, WebSecurityLab,
                              browser_path, browser_xss, memory_database)

LESSON_PATH = ROOT / "tracks/purple/lessons/pu11-web-uygulama-guvenligi.md"


def lesson():
    return parse_lesson(LESSON_PATH.read_text(encoding="utf-8"))


# zero-based task, old solution text, wrong replacement, behavior being tested
MUTATIONS = [
    (0, 'lab.request("PATCH", "/api/documents/1", {"title": "PU05 kalıcı"}, cookie=ayse)',
     'lab.request("GET", "/api/documents/1", cookie=ayse)', "own write must persist"),
    (0, 'baska_yaz["status"]', '200', "foreign status must come from response"),
    (0, 'sonra["revision"] - once["revision"]', 'once["revision"] - once["revision"]', "revision must be measured"),
    (1, 'db.execute(sql, (metin,))',
     'db.execute(sql.replace("?", "\'" + metin + "\'"))', "SQL value binding"),
    (1, 'if siralama not in siralar:', 'if False:', "ORDER BY allowlist"),
    (1, '"yazar": "yazar ASC, id ASC"', '"yazar": "yazar DESC, id ASC"', "author direction"),
    (2, 'dom.text(metin)', 'dom.html(metin)', "textContent instead of innerHTML"),
    (2, 'dom.text(metin)', 'dom.text(__import__("html").escape(metin))', "no double escaping"),
    (3, 'if plan is None or hedef not in plan["hedefler"]:', 'if plan is None:', "target allowlist"),
    (3, 'return list(plan["argv"]) + [hedef]', 'return " ".join(list(plan["argv"]) + [hedef])', "argv not shell string"),
]


class NativeWebSecurityLab(unittest.TestCase):
    def test_loopback_idor_api_persistent_state_and_reset(self):
        with WebSecurityLab() as lab:
            self.assertEqual(lab.server.server_address[0], "127.0.0.1")
            ayse = lab.login("ayse")
            can = lab.login("can")
            self.assertEqual(lab.request("POST", "/session", {"user": "ayse", "password": "wrong"})["status"], 401)
            self.assertEqual(lab.request("GET", "/api/documents/1")["status"], 401)
            self.assertEqual(lab.request("GET", "/api/documents/999", cookie=ayse)["status"], 404)
            self.assertEqual(lab.request("GET", "/api/documents/2", cookie=ayse)["status"], 403)
            self.assertEqual(lab.request("GET", "/api/documents", cookie=ayse)["body"]["records"],
                             [{"id": 1, "owner": "ayse", "title": "Ayşe taslağı"}])
            before = lab.snapshot()
            denied = lab.request("PATCH", "/api/documents/2", {"title": "yetkisiz"}, cookie=ayse)
            self.assertEqual(denied["status"], 403)
            self.assertEqual(lab.snapshot(), before)
            accepted = lab.request("PATCH", "/api/documents/1", {"title": " kalıcı "}, cookie=ayse)
            self.assertEqual((accepted["status"], accepted["body"]["title"]), (200, "kalıcı"))
            self.assertEqual(lab.snapshot()["revision"], 1)
            rejected = lab.request("PATCH", "/api/documents/1", {"title": "x", "owner": "can"}, cookie=ayse)
            self.assertEqual(rejected["status"], 422)
            self.assertEqual(lab.snapshot()["documents"][1]["owner"], "ayse")
            self.assertEqual(lab.snapshot()["revision"], 1)
            self.assertEqual(lab.request("PATCH", "/api/documents/1", {"title": "Can yazdı"}, cookie=can)["status"], 403)
            self.assertEqual(lab.request("POST", "/_control/reset")["status"], 403)
            reset = lab.request("POST", "/_control/reset", headers={"X-Lab-Control": lab.control})
            self.assertEqual(reset["status"], 200)
            self.assertEqual(lab.snapshot(), before)
            self.assertEqual(lab.request("GET", "/api/documents/1", cookie=ayse)["status"], 401)

    def test_in_memory_sqlite_and_safe_dom_model(self):
        db = memory_database()
        try:
            self.assertEqual(db.execute("PRAGMA database_list").fetchone()[2], "")
            self.assertEqual(db.execute("SELECT count(*) FROM notlar").fetchone()[0], 3)
        finally:
            db.close()
        dom = DOMModel()
        dom.text(CANARY)
        self.assertFalse(dom.canary)
        self.assertEqual(dom.serialized(), "&lt;script&gt;window.__paftaCanary=1&lt;/script&gt;")
        unsafe = DOMModel()
        unsafe.html(CANARY)
        self.assertTrue(unsafe.canary)

    def test_command_fixture_is_data_only(self):
        original = deepcopy(COMMAND_PLANS)
        plan = list(COMMAND_PLANS["durum"]["argv"]) + ["web01"]
        self.assertEqual(plan, ["pafta-durum", "--format", "json", "--hedef", "web01"])
        plan[0] = "değişti"
        self.assertEqual(COMMAND_PLANS, original)
        self.assertNotIn("web01;whoami", COMMAND_PLANS["durum"]["hedefler"])


@unittest.skipUnless(os.environ.get("PAFTA_WEB_BROWSER") == "1",
                     "SKIP: gerçek tarayıcı canary'si opt-in; PAFTA_WEB_BROWSER=1 gerekir")
class BrowserXSS(unittest.TestCase):
    def setUp(self):
        if not browser_path():
            self.skipTest("SKIP: kurulu Edge/Chromium yok; güvenli DOM modeli ayrıca test edilir")

    def test_harmless_real_browser_canary(self):
        with WebSecurityLab() as lab:
            result = browser_xss(lab)
        self.assertEqual(result, {"raw": True, "safe": False})


class Curriculum(unittest.TestCase):
    def test_prediction_solutions_and_starters(self):
        parsed = lesson()
        self.assertEqual(parsed["id"], "pu11")
        self.assertEqual(sum(step["kind"] == "tahmin" for step in parsed["steps"]), 1)
        tasks = [step for step in parsed["steps"] if step["kind"] == "gorev"]
        self.assertEqual(len(tasks), 4)
        for step in parsed["steps"]:
            runner = get("purple")
            with self.subTest(step=step["kind"], title=step["title"]):
                if step["kind"] == "gorev":
                    solution = runner.test(step["solution"], step)
                    self.assertEqual(solution["status"], "pass", solution)
                    starter = runner.test(step["starter"], step)
                    self.assertEqual(starter["status"], "fail", starter)
                elif step["kind"] == "tahmin":
                    result = runner.run(step["code"], setup=step.get("setup"))
                    self.assertEqual(result["status"], "ok", result)
                    output = "".join(text for kind, text in result.get("segs", []) if kind == "out")
                    self.assertEqual(output, "200 403 401\n")

    def test_behavioral_wrong_answers_are_rejected(self):
        tasks = [step for step in lesson()["steps"] if step["kind"] == "gorev"]

        def execute(case):
            index, old, new, name = case
            task = tasks[index]
            if old not in task["solution"]:
                return name, {"status": "missing", "old": old}
            wrong = task["solution"].replace(old, new, 1)
            return name, get("purple").test(wrong, task)

        with ThreadPoolExecutor(max_workers=2) as pool:
            for name, result in pool.map(execute, MUTATIONS):
                with self.subTest(mutation=name):
                    self.assertEqual(result["status"], "fail", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
