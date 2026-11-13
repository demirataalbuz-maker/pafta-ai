"""Runner transport tests; --native opts into the existing installed Splunk lab.

No Docker start/image download is performed here. Native mode requires its API
already ready; failures remain failures instead of falling back to local Sigma.
"""
import argparse
import json
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.runners import SigmaSplunkRunner,for_step,get
from engine.lessons import Library

class Transport(unittest.TestCase):
 def test_single_pipeline_priority_is_not_a_detection_threshold(self):
  from sandbox.py_harness import _sgs_cevir
  step=Library().lesson('sigma','sg19')['steps'][2]
  rules=[]
  exec(step['setup'],{'props':lambda *a,**k:None,'veri':lambda *a,**k:None,'kural':rules.append})
  original={'girdi':'pipeline','code':step['solution']}
  changed=dict(original,code=step['solution'].replace('priority: 100','priority: 101'))
  self.assertIn('priority: 100',original['code'])
  self.assertEqual(_sgs_cevir(original,rules[0]),_sgs_cevir(changed,rules[0]),'Priority is not a rule threshold: this single composed pipeline produces identical SPL')

 def invoke(self,runner,action,status):
  jobs=[]
  class Child:
   def __init__(self,cmd,**kw):
    jobs.append(json.loads(Path(cmd[-2]).read_text(encoding='utf-8')))
    Path(cmd[-1]).write_text(json.dumps({'status':status,'segs':[]}),encoding='utf-8')
   def communicate(self,timeout=None):return b'',b''
  with patch('sandbox.splunk_lab.hazirla',return_value=None),patch('engine.runners.subprocess.Popen',Child):result=action()
  self.assertEqual(result['status'],status)
  return jobs[0]

 def test_modes_and_metadata(self):
  for girdi in ('kural','pipeline'):
   runner=SigmaSplunkRunner(girdi,'sysmon,windows')
   job=self.invoke(runner,lambda:runner.run('title: probe','input','setup'), 'ok')
   self.assertEqual((job['mode'],job['girdi'],job['pipeline'],job['setup']),('sgs_run',girdi,'sysmon,windows','setup'))
   job=self.invoke(runner,lambda:runner.test('source',{'test':'ok(True)','setup':'prepare'}),'pass')
   self.assertEqual((job['mode'],job['girdi'],job['test']),('sgs_test',girdi,'ok(True)'))
  with self.assertRaises(ValueError):SigmaSplunkRunner('unknown')

 def test_dispatch_and_errors_never_fall_back(self):
  step=Library().lesson('sigma','sg19')['steps'][2]
  runner=for_step(get('sigma'),step)
  self.assertIsInstance(runner,SigmaSplunkRunner)
  self.assertEqual(runner.ek['girdi'],'pipeline')
  for status in ('error','internal','timeout'):
   job=self.invoke(runner,lambda:runner.test('invalid',step),status)
   self.assertEqual(job['mode'],'sgs_test')

 def test_real_child_timeout_is_reported(self):
  class Slow:
   pid=0
   def __init__(self,*args,**kw):self.calls=0
   def communicate(self,timeout=None):
    self.calls+=1
    if self.calls==1:raise subprocess.TimeoutExpired('probe',timeout)
    return b'',b''
  with patch('sandbox.splunk_lab.hazirla',return_value=None),patch('engine.runners.subprocess.Popen',Slow),patch('engine.runners._kill_tree') as kill:
   result=SigmaSplunkRunner().run('probe',timeout=1)
  self.assertEqual(result['status'],'timeout')
  kill.assert_called_once()

class Native(unittest.TestCase):
 def test_pipeline_actual_splunk(self):
  from sandbox import splunk_lab
  self.assertTrue(splunk_lab._api_acik(),'Start the existing Splunk lab manually; this test never installs')
  step=Library().lesson('sigma','sg19')['steps'][2]
  with patch('sandbox.splunk_lab.hazirla',return_value=None):
   result=for_step(get('sigma'),step).test(step['solution'],step)
  self.assertEqual(result['status'],'pass',result)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--native',action='store_true')
 args=parser.parse_args()
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Transport)
 if args.native:suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Native))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 sys.exit(not result.wasSuccessful())
