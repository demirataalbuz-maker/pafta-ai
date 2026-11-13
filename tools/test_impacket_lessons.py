"""Real WSL/Impacket acceptance and mutation checks for P78/P79.

No package installs. Run from Windows or Git Bash:
    python tools/test_impacket_lessons.py
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
IDS = ("p78", "p79")


def steps(lid, kind):
    return [s for s in LIB.lesson("python", lid)["steps"] if s["kind"] == kind]


def runner(st):
    return for_step(get("python"), st)


# Each edit is a realistic error, not a change to the grading environment.
MUTATIONS = {('p78', 0): [['authority-lower', '0 <= otorite', '0 < otorite'],
              ['authority-upper', 'otorite <= 2**48 - 1', 'otorite < 2**48 - 1'],
              ['authority-wide', 'otorite <= 2**48 - 1', 'otorite <= 2**48'],
              ['count-exclusive', 'len(altlar) > 15', 'len(altlar) >= 15'],
              ['count-wide', 'len(altlar) > 15', 'len(altlar) > 16'],
              ['sub-lower', '0 <= x', '0 < x'],
              ['sub-upper', 'x <= 2**32 - 1', 'x < 2**32 - 1'],
              ['sub-wide', 'x <= 2**32 - 1', 'x <= 2**32'],
              ['authority-endian', 'otorite.to_bytes(6, "big")', 'otorite.to_bytes(6, "little")'],
              ['sub-endian', 'x.to_bytes(4, "little")', 'x.to_bytes(4, "big")'],
              ['bool-authority', 'type(otorite) is not int', 'not isinstance(otorite, int)'],
              ['bool-sub', 'type(x) is not int', 'not isinstance(x, int)']],
 ('p78', 1): [['header-exclusive', 'len(ham) < 8', 'len(ham) <= 8'],
              ['count-exclusive', 'adet > 15', 'adet >= 15'],
              ['count-wide', 'adet > 15', 'adet > 16'],
              ['revision-ignored', 'ham[0] != 1 or ', ''],
              ['extra-accepted', 'len(ham) != 8 + 4 * adet', 'len(ham) < 8 + 4 * adet'],
              ['short-accepted', 'len(ham) != 8 + 4 * adet', 'len(ham) > 8 + 4 * adet'],
              ['authority-endian', '"Value"], "big"', '"Value"], "little"'],
              ['sub-endian', 'veri[i:i+4], "little"', 'veri[i:i+4], "big"'],
              ['authority-last-byte',
               'sid["IdentifierAuthority"]["Value"]',
               'sid["IdentifierAuthority"]["Value"][-1:]']],
 ('p79', 0): [['lower-exclusive', '0 <= x', '0 < x'],
              ['upper-exclusive', 'x <= 2**64 - 1', 'x < 2**64 - 1'],
              ['upper-wide', 'x <= 2**64 - 1', 'x <= 2**64'],
              ['bool-int', 'type(x) is not int', 'not isinstance(x, int)'],
              ['missing-session', 'p["SessionID"] = oturum', 'p["SessionID"] = 0'],
              ['swapped-ids', 'p["MessageID"] = ileti', 'p["MessageID"] = oturum'],
              ['missing-body', 'p["Data"] = SMB2Echo().getData()', 'p["Data"] = b""'],
              ['wrong-command', 'p["Command"] = SMB2_ECHO', 'p["Command"] = 12']],
 ('p79', 1): [['lower-exclusive', '0 <= beklenen_id', '0 < beklenen_id'],
              ['upper-exclusive', 'beklenen_id <= 2**64 - 1', 'beklenen_id < 2**64 - 1'],
              ['bool-int', 'type(beklenen_id) is not int', 'not isinstance(beklenen_id, int)'],
              ['extra-accepted', 'len(ham) != 64', 'len(ham) < 64'],
              ['wrong-size-accepted', 'p["StructureSize"] != 64', 'p["StructureSize"] < 64'],
              ['flag-equality', 'not flags & 1', 'flags != 1'],
              ['missing-response', 'not flags & 1 or ', ''],
              ['missing-async', 'flags & 2 or ', ''],
              ['missing-compound', 'p["NextCommand"] != 0', 'False'],
              ['missing-command', 'p["Command"] != 13 or ', ''],
              ['missing-message', 'p["MessageID"] != beklenen_id', 'False'],
              ['status-boolean', 'return p["Status"],', 'return bool(p["Status"]),'],
              ['signed-bit', 'bool(flags & 8)', 'bool(flags & 1)'],
              ['session-truncated', 'p["SessionID"], bool', 'p["SessionID"] & 0xFFFFFFFF, bool']]}


class ImpacketLessons(unittest.TestCase):
    def test_layout_and_encoding(self):
        track = LIB.track("python")
        order = [x for m in track["modules"] for x in m["lessons"]]
        self.assertLess(order.index("p78"), order.index("p79"))
        for lid in IDS:
            les = LIB.lesson("python", lid)
            self.assertEqual(len(steps(lid, "gorev")), 4 if lid == "p78" else 2)
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
                    if lid == "p78" and st["title"] == "Eksik paket ile eksik API'yi ayır":
                        self.assertEqual(len(result["checks"]), 8)
                    else:
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
        print(f"{len(jobs)} mutations checked on real Kali Impacket.", flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
