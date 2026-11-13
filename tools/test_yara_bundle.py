"""Real YARA bundle API, curriculum boundaries and source mutation checks."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox.yara_bundle import compile_bundle,scan_bytes,scan_set
from engine.lessons import Library
from engine.runners import get,for_step


class Bundle(unittest.TestCase):
 def test_include_never_reads_host(self):
  for name in ('../secret','/etc/passwd','C:/secret','x\\secret','unknown'):
   with self.subTest(name=name),self.assertRaises(Exception):
    compile_bundle({'a':'include "'+name.replace('\\','\\\\')+'"'},includes={name:'rule X {condition:true}' } if name!='unknown' else {'other':''})
  with self.assertRaises(Exception):compile_bundle({'a':'include "anything"'})

 def test_warning_policy_is_native(self):
  source={'n':'rule X {strings:$a=/a.*b/ condition:$a}'}
  self.assertTrue(compile_bundle(source).warnings)
  with self.assertRaises(Exception):compile_bundle(source,strict=True)

 def test_scan_bounds(self):
  r=compile_bundle({'n':'rule X {condition:true}'})
  for timeout in (0,6,True,1.5):
   with self.assertRaises(ValueError):scan_bytes(r,b'',timeout=timeout)
  with self.assertRaises(ValueError):scan_bytes(r,b'x'*(1048576+1))
  self.assertEqual(len(scan_bytes(r,b'x'*1048576)),1)
  with self.assertRaises(ValueError):scan_set(r,{str(i):b'' for i in range(33)})

 def test_curriculum_predictions_and_mutants(self):
  lib=Library()
  expected={'yr23':"[('sol', 'Isaret')]\n[('sag', 'Isaret'), ('sol', 'Isaret')]\n",'yr24':"[('a.bin', 'ok', [('p', 'X')]), ('b.bin', 'ok', [])]\n"}
  mutations={
   'yr23':[(0,"{'limit': limit}","{'limit': limit+1}"),(0,', dosyalar)',')'),(1,'(m.namespace, m.rule)','m.rule'),(1,'sorted({(m.namespace, m.rule) for m in eslesmeler})','[(m.namespace,m.rule) for m in eslesmeler]')],
   'yr24':[(0,'Path(p).read_bytes()',"b''"),(0,'if len(samples) != len(yollar):','if False:'),(0,'return scan_set(rules, samples)','return []'),(1,'bool(r["matches"])','len(r["matches"])'),(1,'r["status"]=="timeout"','False'),(1,'sum(r["bytes"] for r in rows)','0')]}
  for lid in expected:
   lesson=lib.lesson('yara',lid)
   prediction=next(s for s in lesson['steps'] if s['kind']=='tahmin')
   result=for_step(get('yara'),prediction).run(prediction['code'])
   self.assertEqual(result['status'],'ok',result)
   self.assertEqual(''.join(v for k,v in result['segs'] if k=='out'),expected[lid])
   tasks=[s for s in lesson['steps'] if s['kind']=='gorev']
   for index,old,new in mutations[lid]:
    task=tasks[index]
    self.assertIn(old,task['solution'])
    with self.subTest(lesson=lid,mutation=old):
     result=for_step(get('yara'),task).test(task['solution'].replace(old,new,1),task)
     self.assertEqual(result['status'],'fail',result)


if __name__=='__main__':unittest.main()
