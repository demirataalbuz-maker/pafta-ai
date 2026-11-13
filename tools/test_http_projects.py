"""HT14/HT15 solutions, predictions and focused behavioral mutations.

This checks the lesson tests using the same isolated HTTP runner as the app.
Every mutation below changes a required observable behavior; none is a style
assertion or a source-text restriction on student solutions.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import parse_lesson
from engine.runners import get


def projects():
    return {p.stem[:4]: parse_lesson(p.read_text(encoding="utf-8"))
            for p in (ROOT / "tracks/http/lessons").glob("ht1[45]-*.md")}


# (lesson, zero-based task, old text, changed text, meaning)
MUTATIONS = [
    ("ht14", 0, "port != 80", "port != 81", "default port"),
    ("ht14", 0, "1 <= port <= 65535", "1 < port <= 65535", "port 1"),
    ("ht14", 0, "1 <= port <= 65535", "1 <= port < 65535", "port 65535"),
    ("ht14", 0, 'ord(c) <= 32', 'ord(c) < 32', "literal space in URL"),
    ("ht14", 0, 'ord(c) < 32 and c != "\\t"', 'ord(c) <= 32 and c != "\\t"', "request header value accepts space"),
    ("ht14", 0, 'if govde is not None:', 'if govde:', "empty body still has CL"),
    ("ht14", 0, 'len(govde)}', 'len(govde) + 1}', "exact body length"),
    ("ht14", 0, 'if ":" in u.hostname', 'if False', "IPv6 Host brackets"),
    ("ht14", 0, 'hedef = (u.path or "/")', 'hedef = (u.path or "")', "empty path"),
    ("ht14", 1, 'toplam > azami', 'toplam >= azami', "exact response limit"),
    ("ht14", 1, 'ord(c) < 32 and c != "\\t"', 'ord(c) <= 32 and c != "\\t"', "socket task request header value accepts space"),
    ("ht14", 1, 'toplam > azami', 'toplam > azami + 1', "one excess byte"),
    ("ht14", 1, 'len(govde) < boy:', 'len(govde) <= boy:', "exact CL body"),
    ("ht14", 1, 'len(govde) < boy:', 'len(govde) < boy - 1:', "one missing CL byte"),
    ("ht14", 1, 'govde = govde[:boy]', 'govde = govde[:boy + 1]', "CL does not consume next byte"),
    ("ht14", 1, 'govde[i + boy:i + boy + 2] != b"\\r\\n"', 'False', "chunk delimiter"),
    ("ht14", 1, 'boy = int(boy_metin, 16)', 'boy = int(boy_metin, 10)', "hex chunks"),
    ("ht14", 1, 'len(degerler) != 1', 'len(degerler) > 2', "duplicate CL"),
    ("ht14", 1, 'durum in (204, 304)', 'durum in (204,)', "304 body absent"),
    ("ht14", 1, 'yontem == "HEAD"', 'False', "HEAD body absent"),
    ("ht14", 2, 'sayac >= 5', 'sayac > 5', "sixth redirect"),
    ("ht14", 2, '1 <= port <= 65535', '1 < port <= 65535', "session accepts port 1"),
    ("ht14", 2, 'sayac >= 5', 'sayac >= 4', "fifth redirect"),
    ("ht14", 2, 'omur <= 0', 'omur < 0', "Max-Age zero"),
    ("ht14", 2, 'omur <= 0', 'omur <= 1', "Max-Age one"),
    ("ht14", 2, 'durum == 303 and yontem != "HEAD"', 'durum == 303', "303 preserves HEAD"),
    ("ht14", 2, 'durum in (301, 302) and yontem == "POST"', 'durum in (301, 302)', "301/302 preserve PUT"),
    ("ht14", 2, '{301, 302, 303, 307, 308}', '{301, 302, 303, 307}', "308 redirect"),
    ("ht14", 2, 'if koken != self.koken:', 'if False:', "origin check"),
    ("ht14", 2, 'url = urldefrag(urljoin(url, tablo["location"][-1])).url', 'url = urldefrag(urljoin("http://pafta.test:8080/", tablo["location"][-1])).url', "relative redirect base"),
    ("ht15", 0, "'disabled' not in a", "not a.get('disabled')", "boolean disabled"),
    ("ht15", 0, "self.sabitler.append((a['name'],a.get('value') or ''))", "self.sabitler.append((a['name'],''))", "source hidden values"),
    ("ht15", 0, "len(p.secilenler)>1", "len(p.secilenler)>2", "two selected options"),
    ("ht15", 0, "p.secilenler[0] if p.secilenler else p.secenekler[0]", "p.secenekler[0]", "selected option"),
    ("ht15", 0, "self.select_sayisi+=1", "self.select_sayisi=1", "two priority selects"),
    ("ht15", 1, "1<=len(baslik)<=80", "1<len(baslik)<=80", "one character"),
    ("ht15", 1, "1<=len(baslik)<=80", "1<=len(baslik)<80", "80 characters"),
    ("ht15", 1, "1<=len(baslik)<=80", "0<=len(baslik)<=80", "empty title"),
    ("ht15", 1, "1<=len(baslik)<=80", "1<=len(baslik)<=81", "81 characters"),
    ("ht15", 1, "sonuc['id']<=0", "sonuc['id']<0", "zero record id"),
    ("ht15", 1, "type(sonuc.get('id')) is not int", "not isinstance(sonuc.get('id'),int)", "bool is not record id"),
    ("ht15", 1, "baslik=baslik.strip()", "baslik=baslik", "trim title"),
    ("ht15", 1, "urlencode(alanlar,encoding='utf-8')", "urlencode(dict(alanlar),encoding='utf-8')", "duplicate form names"),
    ("ht15", 1, "urljoin(plan['url'],yerler[0])", "urljoin(sayfa_url,yerler[0])", "Location relative to POST"),
    ("ht15", 1, "durum!=303", "durum not in (302,303)", "exact 303 contract"),
    ("ht15", 1, "if _origin(son)!=_origin(sayfa_url):", "if False:", "redirect origin"),
]


class HttpProjectsTests(unittest.TestCase):
    def test_solutions_starters_and_predictions(self):
        for lid, lesson in projects().items():
            self.assertTrue(any(s["kind"] == "tahmin" for s in lesson["steps"]))
            for index, step in enumerate(lesson["steps"]):
                with self.subTest(lesson=lid, step=index):
                    runner = get("http")
                    if step["kind"] == "gorev":
                        result = runner.test(step["solution"], step)
                        self.assertEqual(result["status"], "pass", result)
                        self.assertNotEqual(runner.test(step["starter"], step)["status"], "pass")
                    elif step["kind"] == "tahmin":
                        result = runner.run(step["code"])
                        self.assertEqual(result["status"], "ok", result)
                        output = "".join(s[1] for s in result.get("segs", []))
                        explanation = step["body"].split("???", 1)[1]
                        for line in output.splitlines():
                            self.assertIn(line, explanation)

    def test_behavioral_mutations(self):
        lessons = projects()
        def execute(case):
            lid, index, old, new, name = case
            task = [s for s in lessons[lid]["steps"] if s["kind"] == "gorev"][index]
            source = task["solution"]
            if old not in source:
                return name, {"status": "missing", "old": old}
            return name, get("http").test(source.replace(old, new, 1), task)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for name, result in pool.map(execute, MUTATIONS):
                with self.subTest(mutation=name):
                    self.assertNotIn(result["status"], ("pass", "missing", "internal", "timeout"), result)


if __name__ == "__main__":
    unittest.main()
