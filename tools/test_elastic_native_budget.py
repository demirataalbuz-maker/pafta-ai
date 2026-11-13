"""Bounded native Elastic queue and --native repeated EL20/EL21 acceptance."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.runners import ElasticRunner,HarnessRunner,get
from engine.lessons import Library

class Budget(unittest.TestCase):
 def test_native_budget_and_explicit_override(self):
  runner=ElasticRunner()
  with patch.object(HarnessRunner,'execute',return_value={'status':'ok'}) as parent:
   runner.run('x',json.dumps({'backend':'elastic'}))
   self.assertEqual(parent.call_args.args[1],120)
   runner.run('x',json.dumps({'backend':'elastic'}),timeout=3)
   self.assertEqual(parent.call_args.args[1],3)
   runner.run('x','{}')
   self.assertIsNone(parent.call_args.args[1])
  self.assertEqual(runner.tavan,300)

 def test_gate_is_bounded_and_released_on_failure(self):
  runner=ElasticRunner();active=0;peak=0;lock=threading.Lock()
  def execute(job,timeout):
   nonlocal active,peak
   with lock:active+=1;peak=max(peak,active)
   try:
    time.sleep(0.02)
    if job['code']=='bad':raise ValueError('native failure')
    return {'status':'ok'}
   finally:
    with lock:active-=1
  def invoke(i):
   try:return runner.run('bad' if i==0 else 'good','{"backend":"elastic"}')
   except ValueError:return 'explicit error'
  with patch.object(HarnessRunner,'execute',side_effect=execute):
   with ThreadPoolExecutor(8) as pool:results=list(pool.map(invoke,range(12)))
  self.assertEqual(peak,2)
  self.assertEqual(results[0],'explicit error')
  self.assertEqual(sum(isinstance(r,dict) for r in results),11)

def native():
 from sandbox.elastic_lab import ready
 ready()
 jobs=[]
 for repeat in range(2):
  for lid in ('el20','el21'):
   for i,s in enumerate(Library().lesson('elastic',lid)['steps']):
    if s['kind'] in ('tahmin','gorev'):jobs.append((repeat,lid,i,s))
 def check(job):
  repeat,lid,i,s=job;start=time.monotonic()
  r=(get('elastic').test(s['solution'],s) if s['kind']=='gorev' else get('elastic').run(s['code'],s.get('stdin',''),s.get('setup')))
  expected='pass' if s['kind']=='gorev' else 'ok'
  if r['status']!=expected:raise AssertionError((lid,i,r))
  return f'{repeat+1} {lid}:{i} {r["status"]} {time.monotonic()-start:.2f}s'
 with ThreadPoolExecutor(8) as pool:
  for line in pool.map(check,jobs):print(line,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',action='store_true');args=p.parse_args()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Budget))
 if not result.wasSuccessful():sys.exit(1)
 if args.native:native()
