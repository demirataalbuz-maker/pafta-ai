"""Real Windows cmd.exe process contract, independent of lesson fixtures."""
import os
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.runners import get


@unittest.skipUnless(os.name == "nt", "native cmd.exe requires Windows")
class CmdRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runner = get("cmd")

    def output(self, code, stdin="", argv=None):
        result = self.runner.run(code, stdin, argv=argv)
        self.assertEqual(result["status"], "ok", result)
        return "".join(text for kind, text in result["segs"] if kind == "out")

    def test_unicode_source_input_and_output(self):
        self.assertEqual(self.output('@echo off\necho İstanbul Çağrı\nset "ad="\nset /p ad=\necho "%ad%"\n',
                                     "Öğrenci\n"), 'İstanbul Çağrı\n"Öğrenci"\n')

    def test_arguments_are_not_reparsed_by_the_launcher(self):
        for argument in ("", "iki kelime", "Çağrı İstanbul", "a&b", "a|b", "a>b", "a<b",
                         "(parantez)", "a^b", "%PATH%", "!veri!", "bitis\\"):
            with self.subTest(argument=argument):
                self.assertEqual(self.output('@echo off\necho "%~1"\n', argv=[argument]),
                                 '"' + argument + '"\n')

    def test_argument_contract_rejects_quotes_newlines_and_nul(self):
        for argument in ('a"b', "a\nb", "a\rb", "a\0b"):
            result = self.runner.run("@echo off\necho calisti\n", argv=[argument])
            self.assertEqual(result["status"], "error", result)
            self.assertEqual(result["kod"], 87)
            self.assertNotIn("calisti", "".join(t for _, t in result["segs"]))

    def test_exit_code_and_stderr(self):
        result = self.runner.run("@echo off\necho uyari 1>&2\nexit /b 7\n")
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(result["kod"], 7)
        self.assertEqual(result["error"]["kod"], 7)
        self.assertIn("uyari", "".join(t for k, t in result["segs"] if k == "err"))

    def test_current_directory_search_can_be_disabled(self):
        with patch.dict(os.environ, {"NoDefaultCurrentDirectoryInExePath": "1"}):
            self.assertEqual(self.output('@echo off\necho "hazır %~1"\n', argv=["iki öğe & % ! ^"]),
                             '"hazır iki öğe & % ! ^"\n')
            step = {"test": 'eq(out, "hazir\\n")\neq(run(argv=["tekrar"]), "tekrar\\n")'}
            code = '@echo off\nif "%~1"=="" (echo hazir) else (echo %~1)\nexit /b 0\n'
            self.assertEqual(self.runner.test(code, step)["status"], "pass")

    def test_git_bash_path_uses_windows_find_and_sort(self):
        bash = Path(r"C:\Program Files\Git\bin\bash.exe")
        if not bash.is_file():
            self.skipTest("Git Bash kurulu değil")
        command = 'export PATH="/usr/bin:/bin:$PATH"; exec "$1" -X utf8 "$2" --git-bash-probe'
        result = subprocess.run([str(bash), "-c", command, "pafta-cmd-path-test",
                                 sys.executable.replace("\\", "/"), str(Path(__file__).resolve()).replace("\\", "/")],
                                capture_output=True, text=True, encoding="utf-8", timeout=30,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertEqual(result.returncode, 0, result.stderr)
        probe = json.loads(result.stdout)
        # Prove the parent really prioritizes Git's tools; a normal Windows
        # launch would not reproduce the audit finding.
        self.assertIn("git", probe["parent_path"].split(";")[0].lower())
        self.assertEqual(probe["status"], "ok", probe)
        expected = str(Path(os.environ["SystemRoot"]) / "System32").lower()
        self.assertEqual(probe["sort"].lower(), expected + r"\sort.exe")
        self.assertEqual(probe["find"].lower(), expected + r"\find.exe")
        self.assertEqual(probe["output"], "alfa\nzeta\n2\n")

    def test_input_file_supports_multiple_native_line_reads(self):
        code = '@echo off\nset "a="\nset "b="\nset /p a=\nset /p b=\necho "%a%"\necho "%b%"\nexit /b 0\n'
        for stdin in ("bir\niki\n", "bir\r\niki\r\n"):
            self.assertEqual(self.output(code, stdin), '"bir"\n"iki"\n')

    def test_delayed_expansion_starts_disabled_and_is_opt_in(self):
        code = '@echo off\nset "n=1"\n(\nset "n=2"\necho %n%\n)\nsetlocal enabledelayedexpansion\n(\nset "n=3"\necho !n!\n)\n'
        self.assertEqual(self.output(code), "1\n3\n")
        self.assertEqual(self.output('@echo off\nset "n=7"\necho !n!\n'), "!n!\n")

    def test_proc_helpers_use_native_exit_status(self):
        step = {"test": 'eq(out, "ok\\n")\neq(calis(argv=["bad"])["kod"], 9)\neq(run(argv=["two words"]), "two words\\n")'}
        code = '@echo off\nif "%~1"=="bad" exit /b 9\nif "%~1"=="" (echo ok) else (echo %~1)\nexit /b 0\n'
        result = self.runner.test(code, step)
        self.assertEqual(result["status"], "pass", result)

    def test_setup_and_working_directory_are_disposable(self):
        setup = 'from pathlib import Path\nPath("ornek.txt").write_text("hazir\\n", encoding="utf-8")'
        self.assertEqual(self.runner.run('@type ornek.txt\n', setup=setup)["status"], "ok")
        self.assertEqual(self.output('@if exist ornek.txt (echo var) else (echo yok)\n'), "yok\n")

    def test_no_fake_trace_or_bytecode(self):
        self.assertFalse(self.runner.ozellik["roentgen"])
        self.assertIsNone(self.runner.trace("echo test"))
        self.assertIsNone(self.runner.dis("echo test"))

    def test_native_timeout_returns_without_hanging_the_harness(self):
        proc = dict(self.runner.ek["proc"], sure=1)
        result = self.runner.execute({"mode": "proc_run", "proc": proc,
                                      "code": "@echo off\n:again\ngoto again\n"}, timeout=6)
        self.assertEqual(result["status"], "timeout", result)
        self.assertEqual(result["error"]["type"], "Zaman aşımı")


if __name__ == "__main__":
    if sys.argv[1:] == ["--git-bash-probe"]:
        code = '@echo off\nwhere sort\nwhere find\n>adlar.txt echo zeta\n>>adlar.txt echo alfa\ntype adlar.txt|sort /l C\ntype adlar.txt|find /c "a"\n'
        result = get("cmd").run(code)
        lines = "".join(t for k, t in result.get("segs", []) if k == "out").splitlines()
        sorts = [line for line in lines if line.lower().endswith("sort.exe")]
        finds = [line for line in lines if line.lower().endswith("find.exe")]
        output = "\n".join(line for line in lines if not line.lower().endswith(("sort.exe", "find.exe"))) + "\n"
        print(json.dumps({"parent_path": os.environ.get("PATH", ""), "status": result["status"],
                          "sort": sorts[0] if sorts else "", "find": finds[0] if finds else "", "output": output,
                          "error": result.get("error")}, ensure_ascii=False))
    else:
        unittest.main(verbosity=2)
