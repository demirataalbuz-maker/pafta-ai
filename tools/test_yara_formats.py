"""Real libyara predictions and semantic mutation checks for YR21–YR22."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get
from sandbox.yara_format_fixtures import format_fixture
from sandbox.yara_engine import compile_rules, match_rules, decode_data


class FormatLessons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library, cls.runner = Library(), get('yara')

    def step(self, lesson, index):
        return self.library.lesson('yara', lesson)['steps'][index]

    def test_predictions(self):
        for lesson, expected in (('yr21', 'Nesne\nEsik\n'), ('yr22','PE\nManaged\n')):
            step = self.step(lesson,1)
            self.assertEqual(decode_data(step['stdin']),format_fixture('elf256' if lesson=='yr21' else 'net2'))
            result = self.runner.run(step['code'],step['stdin'])
            self.assertEqual(result['status'],'ok',result)
            self.assertEqual(result['segs'],[['out',expected]])

    def test_solutions_and_starters(self):
        for lesson in ('yr21','yr22'):
            for index in (2,3):
                step = self.step(lesson,index)
                with self.subTest(lesson=lesson, index=index):
                    self.assertEqual(self.runner.test(step['solution'],step)['status'],'pass')
                    self.assertEqual(self.runner.test(step['starter'],step)['status'],'fail')

    def test_mutations(self):
        mutations = (
            ('yr21',2,'elf.EM_X86_64','elf.EM_386'),
            ('yr21',2,'elf.ET_REL','elf.ET_DYN'),
            ('yr21',2,' and ',' or '),
            ('yr21',3,'s.size >= 256','s.size > 256'),
            ('yr21',3,'s.size >= 256','s.size >= 255'),
            ('yr21',3,'s.size >= 256','s.size <= 256'),
            ('yr21',3,'s.name == ".pafta"','true'),
            ('yr21',3,'(s.flags & elf.SHF_WRITE) == 0','true'),
            ('yr21',3,'for any s','for all s'),
            ('yr22',2,'major >= 2','major > 2'),
            ('yr22',2,'major >= 2','major >= 1'),
            ('yr22',2,'major <= 3','major < 3'),
            ('yr22',2,'major <= 3','major <= 4'),
            ('yr22',2,'dotnet.assembly.name == "PaftaLab"','true'),
            ('yr22',3,'c.fullname == "Pafta.Sample.Marker"','c.name == "Marker"'),
            ('yr22',3,'for any c','for all c'),
            ('yr22',3,'"Pafta.Sample.Marker"','"Other.Sample.Marker"'),
        )
        for lesson,index,old,new in mutations:
            step = self.step(lesson,index)
            self.assertEqual(step['solution'].count(old),1,(lesson,old))
            with self.subTest(lesson=lesson,index=index,mutation=(old,new)):
                result = self.runner.test(step['solution'].replace(old,new),step)
                self.assertEqual(result['status'],'fail',result)
                self.assertIsNone(result.get('error'),result)
                self.assertTrue(any(not c['ok'] for c in result['checks']),result)

    def test_fixture_integrity_and_native_modules(self):
        records=json.loads((ROOT/'tracks/yara/fixtures/formats.json').read_text(encoding='utf-8'))
        self.assertEqual(len(records),13)
        elf=compile_rules('import "elf" rule e { condition: elf.type == elf.ET_REL }')
        net=compile_rules('import "dotnet" rule n { condition: dotnet.is_dotnet }')
        for name in records:
            data=format_fixture(name)  # includes SHA256 verification
            self.assertGreater(len(data),64)
            if name.startswith('net'):
                self.assertTrue(match_rules(net,data),name)
                self.assertFalse(match_rules(elf,data),name)
            else:
                self.assertFalse(match_rules(net,data),name)
                self.assertEqual(bool(match_rules(elf,data)),name!='elf_dyn',name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
