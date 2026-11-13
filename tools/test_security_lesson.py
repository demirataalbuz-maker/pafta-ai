"""JV15 real framework reproduction and modeled reading-task mutation tests."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get
from tools.security_lab import run


class Security(unittest.TestCase):
 def test_real_framework_prediction(self):
  step=next(s for s in Library().lesson('java','jv15')['steps'] if s['kind']=='tahmin')
  norm=lambda s:[' '.join(v.split()) for v in s.splitlines() if v.strip()]
  self.assertEqual(norm(run()),norm(step['gercek']))

 def test_reading_task_mutants(self):
  tasks=[s for s in Library().lesson('java','jv15')['steps'] if s['kind']=='gorev']
  cases=[
   (0,'yol == onek or ',''),
   (0,'yol.startswith(onek + "/")','yol.startswith(onek)'),
   (0,'if yetkiler is None:','if not yetkiler:'),
   (0,'for kalip, gereken in kurallar:','for kalip, gereken in reversed(kurallar):'),
   (0,'kalip == yol','kalip.lower() == yol.lower()'),
   (1,'cagriYolu[0]','cagriYolu[-1]'),
   (1,'return None','return "IZIN"'),
   (1,'gereken in yetkiler','gereken not in yetkiler')]
  # Exact path equality mutation needs a witness beyond existing prefix cases.
  for index,old,new in cases:
   task=tasks[index]
   self.assertIn(old,task['solution'])
   with self.subTest(task=index,mutation=old):
    result=get('python').test(task['solution'].replace(old,new,1),task)
    self.assertEqual(result['status'],'fail',result)


if __name__=='__main__':unittest.main()
