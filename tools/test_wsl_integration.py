"""Real Kali WSL routing through temporary lessons, HTTP, exams and validate.

    python tools/test_wsl_integration.py

Requires the configured WSL distribution; never installs packages or modifies
real lessons/progress. Runtime/process cleanup tests live in test_wsl_runtime.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import server
from engine import runners, sinav
from engine.lessons import Library, parse_lesson
import validate


PY_LESSON = '''---
id: p01
title: Linux yönlendirme deneyi
summary: Yalnız testte oluşturulan geçici ders.
backend: wsl
timeout: 120
---
::: anlat Örnek
```python
import sys
assert sys.platform == "linux"
print("Linux")
```
:::
::: tahmin İşletim sistemi
```python
import sys
print(sys.platform)
```
???
Linux yorumlayıcısında linux yazılır.
:::
::: gorev Gerçek Linux üzerinde
```setup
import sys
from pathlib import Path
assert sys.platform == "linux", "Görev Linux üzerinde çalışmalı"
Path("çalışma.txt").write_text("merhaba\\n", encoding="utf-8")
```
```starter
value = "yanlış"
```
```solution
import sys
value = sys.platform
```
```test
eq(value, "linux", "Linux yorumlayıcısının gerçek sonucu")
```
:::
::: tahmin Yerel karşılaştırma
```meta
backend: native
timeout: 6
```
```python
import sys
print(sys.platform)
```
???
Windows yorumlayıcısında win32 yazılır.
:::
'''

BASH_LESSON = '''---
id: b01
title: Linux Bash yönlendirme deneyi
summary: Yalnız testte oluşturulan geçici ders.
backend: wsl
timeout: 120
---
::: tahmin Çekirdek
```bash
uname -s
```
???
Linux yazılır.
:::
::: gorev Çekirdeği yazdır
```starter
printf 'yanlış\\n'
```
```solution
uname -s
```
```test
eq(run(), "Linux\\n")
```
:::
'''


def output(result):
    return "".join(text for kind, text in result.get("segs", []) if kind == "out")


class MetadataTests(unittest.TestCase):
    def test_lesson_defaults_and_explicit_step_override(self):
        lesson = parse_lesson(PY_LESSON)
        self.assertEqual(lesson["steps"][0]["meta"], {"backend": "wsl", "timeout": 120})
        self.assertEqual(lesson["steps"][2]["meta"], {"backend": "wsl", "timeout": 120})
        self.assertEqual(lesson["steps"][3]["meta"], {"backend": "native", "timeout": 6})
        ordinary = parse_lesson("---\nid: local\n---\n::: tahmin\n```python\nprint(1)\n```\n:::")
        self.assertEqual(ordinary["steps"][0]["meta"], {})

    def test_unknown_backend_is_a_validation_error(self):
        with patch.dict(validate.RUNNER_ADI, {"python": "python"}):
            result = validate.run_job(("ornek", "python", "temporary", {"meta": {"backend": "typo"}}, "print(1)"))
        self.assertFalse(result[0])
        self.assertEqual(result[1], "KOŞUCU AYARI")


class WslIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pafta_wsl_api_")
        cls.environment = patch.dict(os.environ, {"PAFTA_DATA": str(Path(cls.temp.name) / "progress")})
        cls.environment.start()
        tracks = Path(cls.temp.name) / "tracks"
        for tid, lid, source in (("python", "p01", PY_LESSON), ("bash", "b01", BASH_LESSON)):
            folder = tracks / tid
            (folder / "lessons").mkdir(parents=True)
            (folder / "track.json").write_text(json.dumps({
                "id": tid, "name": tid, "runner": tid, "status": "active",
                "modules": [{"title": "Geçici", "lessons": [lid]}],
            }), encoding="utf-8", newline="\n")
            (folder / "lessons" / (lid + "-temporary.md")).write_text(source, encoding="utf-8", newline="\n")
        cls.app, cls.httpd = server.start(0)
        cls.app.lib = Library(str(tracks))
        cls.base = f"http://127.0.0.1:{cls.app.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.environment.stop()
        cls.temp.cleanup()

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, headers={
            "X-Pafta-Token": self.app.token, "Origin": self.base, "Content-Type": "application/json",
        })
        with urllib.request.urlopen(request, timeout=150) as response:
            return json.load(response)

    def test_run_uses_authoritative_lesson_backend_and_linux_working_directory(self):
        result = self.request("/api/run", {
            "track": "python", "lesson": "p01", "step": 2, "backend": "native",
            "code": "import os, sys, json\nfrom pathlib import Path\nprint(json.dumps([sys.platform, os.getcwd(), Path('çalışma.txt').read_text(encoding='utf-8')]))",
        })
        self.assertEqual(result["status"], "ok", result)
        platform, cwd, fixture = json.loads(output(result))
        self.assertEqual(platform, "linux")
        self.assertTrue(cwd.startswith("/tmp/"), cwd)
        self.assertNotIn("/mnt/", cwd)
        self.assertEqual(fixture, "merhaba\n")
        public = self.request("/api/lesson/python/p01")["lesson"]["steps"][2]
        self.assertEqual(public["meta"]["backend"], "wsl")
        self.assertFalse({"test", "solution", "setup"} & public.keys())

    def test_check_and_guess_use_linux_and_keep_native_override(self):
        for tid, lid, prediction_index, task_index, expected in (
            ("python", "p01", 1, 2, "linux"), ("bash", "b01", 0, 1, "Linux"),
        ):
            payload = {"track": tid, "lesson": lid, "step": prediction_index}
            self.assertTrue(self.request("/api/guess", dict(payload, guess=expected))["correct"])
            self.assertFalse(self.request("/api/guess", dict(payload, guess="yanlış"))["correct"])
            task = self.app.lib.lesson(tid, lid)["steps"][task_index]
            payload["step"] = task_index
            self.assertEqual(self.request("/api/check", dict(payload, code=task["solution"]))["status"], "pass")
            self.assertNotEqual(self.request("/api/check", dict(payload, code=task["starter"]))["status"], "pass")
        native = self.request("/api/guess", {"track": "python", "lesson": "p01", "step": 3, "guess": sys.platform})
        self.assertTrue(native["correct"], native)

    def test_run_trace_dis_and_standalone_selection(self):
        payload = {"track": "python", "lesson": "p01", "step": 1,
                   "code": 'import sys\nassert sys.platform == "linux"\nprint("çalıştı")'}
        trace = self.request("/api/run", dict(payload, mode="trace"))
        self.assertEqual(trace["status"], "ok", trace)
        dis = self.request("/api/run", dict(payload, mode="dis"))
        self.assertEqual(dis["status"], "ok", dis)
        result = self.request("/api/run", {"track": "python", "backend": "wsl", "code": "import sys\nprint(sys.platform)"})
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(output(result), "linux\n")
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/run", {"track": "python", "backend": "typo", "code": "print(1)"})
        self.assertEqual(error.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/run", {"track": "python", "lesson": "p01", "step": 999, "code": "print(1)"})
        self.assertEqual(error.exception.code, 404)

    def test_exam_grades_each_questions_backend(self):
        now = time.time()
        result = sinav.puanla(self.app.lib, self.app.runner_for, {
            "no": 1, "yol": "python", "sorular": [
                {"lesson": "p01", "step": 1, "kind": "tahmin", "gruplar": ["test"]},
                {"lesson": "p01", "step": 2, "kind": "gorev", "gruplar": ["test"]},
                {"lesson": "p01", "step": 3, "kind": "tahmin", "gruplar": ["test"]},
            ], "gruplar": {"test": {"baslik": "Test", "agirlik": 1}},
            "cevaplar": {"0": "linux", "1": "import sys\nvalue = sys.platform", "2": sys.platform},
            "baslangic": now - 1, "bitis": now + 600, "gecme": 70, "sure_sn": 600,
        })
        self.assertEqual(result["dogru"], 3, result)
        self.assertTrue(result["gecti"])

    def test_validate_runs_examples_predictions_and_both_task_variants(self):
        with patch.dict(validate.RUNNER_ADI, {"python": "python", "bash": "bash"}):
            for tid, lid in (("python", "p01"), ("bash", "b01")):
                jobs = validate.jobs_for(self.app.lib, tid, tid, lid)
                self.assertTrue(jobs)
                for job in jobs:
                    with self.subTest(job=job[:3]):
                        result = validate.run_job(job)
                        self.assertTrue(result[0], result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
