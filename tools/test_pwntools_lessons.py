"""Real WSL/pwntools acceptance and mutation checks for P76/P77.

No package installs. Run from Windows or Git Bash:
    python tools/test_pwntools_lessons.py
"""
from concurrent.futures import ThreadPoolExecutor
import re
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get

LIB = Library()
IDS = ("p76", "p77")


def steps(lid, kind):
    return [s for s in LIB.lesson("python", lid)["steps"] if s["kind"] == kind]


def runner(st):
    return for_step(get("python"), st)


# Each edit is a realistic error, not a change to the grading environment.
MUTATIONS = {
    ("p76", 0): [
        ("lower-exclusive", "-2147483648 <=", "-2147483648 <"),
        ("upper-exclusive", "<= 2147483647", "< 2147483647"),
        ("lower-too-wide", "-2147483648 <=", "-2147483649 <="),
        ("upper-too-wide", "<= 2147483647", "<= 2147483648"),
        ("length-exclusive", "len(veri) > 16", "len(veri) >= 16"),
        ("length-too-wide", "len(veri) > 16", "len(veri) > 17"),
        ("bool-is-int", "type(sayi) is not int", "not isinstance(sayi, int)"),
        ("prefix-endian", 'p16(len(veri), endian="big"', 'p16(len(veri), endian="little"'),
        ("value-endian", 'p32(sayi, endian="little"', 'p32(sayi, endian="big"'),
        ("unsigned-value", "sign=True", "sign=False"),
        ("context-leak", "def cerceve_yaz(sayi, veri):",
         "def cerceve_yaz(sayi, veri):\n    from pwnlib.context import context\n    context.endian = 'little'"),
    ],
    ("p76", 1): [
        ("min-header-exclusive", "len(ham) < 6", "len(ham) <= 6"),
        ("length-exclusive", "uzunluk > 16", "uzunluk >= 16"),
        ("length-too-wide", "uzunluk > 16", "uzunluk > 17"),
        ("allow-trailing", "len(ham) != 6 + uzunluk", "len(ham) < 6 + uzunluk"),
        ("allow-truncated", "len(ham) != 6 + uzunluk", "len(ham) > 6 + uzunluk"),
        ("prefix-endian", 'endian="big"', 'endian="little"'),
        ("value-endian", 'endian="little"', 'endian="big"'),
        ("unsigned-value", "sign=True", "sign=False"),
    ],
    ("p77", 0): [
        ("strip-data", "ham[:-1]", "ham.strip()"),
        ("rstrip-data", "ham[:-1]", "ham.rstrip()"),
        ("keep-newline", "ham[:-1]", "ham"),
        ("empty-line-timeout", 'if ham == b"":', 'if ham in (b"", b"\\n"):'),
        ("eof-as-timeout", 'return "eof", b""', 'return "zaman", b""'),
        ("timeout-as-eof", 'return "zaman", b""', 'return "eof", b""'),
        ("accept-incomplete", 'return "eksik", ham', 'return "tam", ham'),
    ],
    ("p77", 1): [
        ("length-exclusive", "n > 16", "n >= 16"),
        ("length-too-wide", "n > 16", "n > 17"),
        ("signed-prefix", "sign=False", "sign=True"),
        ("wrong-endian", 'endian="big"', 'endian="little"'),
        ("header-recv", "t.recvn(2,", "t.recv(2,"),
        ("body-recv", "t.recvn(n,", "t.recv(n,"),
        ("empty-body-timeout", 'if n == 0:\n            return "tam", b""',
         'if n == 0:\n            return "zaman", b""'),
        ("eof-as-timeout", 'return "eof", b""', 'return "zaman", b""'),
        ("timeout-as-eof", 'return "zaman", b""', 'return "eof", b""'),
    ],
}


class PwntoolsLessons(unittest.TestCase):
    def test_layout_and_encoding(self):
        track = LIB.track("python")
        order = [x for m in track["modules"] for x in m["lessons"]]
        self.assertLess(order.index("p76"), order.index("p77"))
        for lid in IDS:
            les = LIB.lesson("python", lid)
            self.assertEqual(len(steps(lid, "gorev")), 2)
            self.assertEqual(len(steps(lid, "tahmin")), 1)
            self.assertTrue(all(s["meta"]["backend"] == "wsl" for s in les["steps"]))
            path, = (ROOT / "tracks/python/lessons").glob(lid + "-*.md")
            raw = path.read_bytes()
            raw.decode("utf-8")
            self.assertNotIn(b"\r", raw)

    def test_predictions_match_printed_answer(self):
        for lid in IDS:
            st, = steps(lid, "tahmin")
            answer = re.search(r"```text\n(.*?)```", st["body"].split("???", 1)[1], re.S)
            self.assertIsNotNone(answer)
            result = runner(st).run(st["code"], setup=st.get("setup"))
            self.assertEqual(result["status"], "ok", result)
            self.assertEqual("".join(s[1] for s in result["segs"] if s[0] == "out"),
                             answer.group(1))
            self.assertFalse([s for s in result["segs"] if s[0] == "err"], result)
            self.assertTrue(result.get("runtime", {}).get("python"), result)

    def test_solutions_and_starters(self):
        for lid in IDS:
            for st in steps(lid, "gorev"):
                with self.subTest(lid=lid, title=st["title"]):
                    result = runner(st).test(st["solution"], st)
                    self.assertEqual(result["status"], "pass", result)
                    self.assertGreater(len(result["checks"]), 10)
                    bad = runner(st).test(st["starter"], st)
                    self.assertIn(bad["status"], ("fail", "error"), bad)

    def test_mutations_are_rejected(self):
        jobs = []
        for (lid, idx), edits in MUTATIONS.items():
            st = steps(lid, "gorev")[idx]
            for name, old, new in edits:
                self.assertIn(old, st["solution"], (lid, name))
                code = st["solution"].replace(old, new, 1)
                jobs.append((f"{lid}/{idx}/{name}", st, code))

        def check(job):
            name, st, code = job
            result = runner(st).test(code, st)
            return name, result

        with ThreadPoolExecutor(max_workers=4) as pool:
            for name, result in pool.map(check, jobs):
                with self.subTest(mutation=name):
                    self.assertIn(result["status"], ("fail", "error"), result)
        print(f"{len(jobs)} mutations checked on real Kali pwntools.", flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
