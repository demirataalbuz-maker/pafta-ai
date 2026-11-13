"""AD24–25 actual parsers, prediction outputs and boundary mutation rejection."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get,for_step

CASES=[
 ('ad24',0,'p.optionxform=str','p.optionxform=str.lower'),
 ('ad24',0,".removeprefix('*')",''),
 ('ad24',0,"if p.has_section('Privilege Rights') else {}","if False else {}"),
 ('ad24',1,"!='S-1-5-32-544'","!='S-1-5-32-545'"),
 ('ad24',1,"group.get('disabled')=='1'",'False'),
 ('ad24',1,"p.get('deleteAllGroups')=='1'",'False'),
 ('ad24',1,"group.find('Filters') is not None",'False'),
 ('ad24',2,'len(raw)>=8','len(raw)>8'),
 ('ad24',2,'0x67655250,1','0x67655250,2'),
 ('ad25',0,'<=int(now)','<int(now)'),
 ('ad25',0,"int(v['t'],16)","int(v['t'])"),
 ('ad25',1,"row.get('permission')=='denied'",'False'),
 ('ad25',1,"row.get('permission')!='allowed'",'False'),
 ('ad25',1,"row.get('encrypted_present')",'False'),
]

class Policy(unittest.TestCase):
 def test_predictions(self):
  expected={'ad24':'2\n*S-1-5-32-544\n','ad25':"['n', 'p', 't']\nAdministrator\n"}
  for lid,value in expected.items():
   lesson=Library().lesson('ad',lid)
   step=next(s for s in lesson['steps'] if s['kind']=='tahmin')
   r=for_step(get('ad'),step).run(step['code'])
   self.assertEqual(r['status'],'ok',r)
   self.assertEqual(''.join(v for k,v in r['segs'] if k=='out'),value)
 def test_mutations(self):
  for lid,index,old,new in CASES:
   step=[s for s in Library().lesson('ad',lid)['steps'] if s['kind']=='gorev'][index]
   self.assertIn(old,step['solution'])
   with self.subTest(lesson=lid,old=old):
    r=for_step(get('ad'),step).test(step['solution'].replace(old,new,1),step)
    self.assertEqual(r['status'],'fail',r)

if __name__=='__main__':unittest.main()
