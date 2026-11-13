"""JV16 gerçek motor yeniden üretimi ve yanlış çözüm reddi testleri."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get
from tools.template_lab import run


class TemplateLesson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lesson = Library().lesson('java', 'jv16')

    def test_real_engine_prediction(self):
        step = next(s for s in self.lesson['steps'] if s['kind'] == 'tahmin')
        normalize = lambda value: [' '.join(line.split()).replace(' :', ':')
                                   for line in value.splitlines() if line.strip()]
        self.assertEqual(normalize(run()), normalize(step['gercek']))

    def test_saved_measurement(self):
        saved = (ROOT / 'outputs/java-template-real.txt').read_text(encoding='utf8')
        self.assertEqual(run(), saved.replace('\r\n', '\n'))

    def test_wrong_solutions_are_rejected(self):
        tasks = [s for s in self.lesson['steps'] if s['kind'] == 'gorev']
        cases = [
            (0, '("&", "&amp;"), ("<", "&lt;")', '("<", "&lt;"), ("&", "&amp;")'),
            (0, '("\\\"", "&quot;"), ("\'", "&#39;")', '("\\\"", "&quot;")'),
            (0, 'if kip != "kacir":', 'if kip == "kacir":'),
            (0, 'return deger\n', 'return None\n'),
            (1, 'if motor == "thymeleaf":', 'if motor == "freemarker":'),
            (1, 'return "kacar" if html else "ham"', 'return "ham" if html else "kacar"'),
            (1, 'return None if html else "kacar"', 'return "kacar"'),
            (1, 'return "ham" if html else None', 'return "ham"'),
            (1, 'if ifade in ("th:text", "[[..]]"):', 'if ifade in ("th:text", "th:utext", "[[..]]", "[(..)]"):'),
            (2, 'return (sonuc + kalan, "kod" if bulundu else "veri")',
                'return (sonuc + kalan, "veri" if bulundu else "kod")'),
            (2, 'str(veri.get(ad, ""))', 'str(veri.get(ad, "sabit"))'),
            (2, 'ad = kalan[bas + 4:son]', 'ad = kalan[bas:son]'),
            (2, 'sonuc += kalan[:bas] + str(veri.get(ad, ""))',
                'sonuc += str(veri.get(ad, ""))'),
        ]
        for index, old, new in cases:
            task = tasks[index]
            self.assertIn(old, task['solution'])
            with self.subTest(task=index, mutation=old):
                result = get('python').test(task['solution'].replace(old, new, 1), task)
                self.assertNotEqual(result['status'], 'pass', result)


if __name__ == '__main__':
    unittest.main()
