"""Wall-clock pacing regression; --native repeats the real SP22 predictions."""
import argparse
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox.splunk_lab import dispatch_after,verify_dispatch_window,SplunkHatasi

class Timing(unittest.TestCase):
 def test_late_product_result_is_not_a_wrong_prediction(self):
  verify_dispatch_window(0,12,previous=2,clock=lambda:4)
  self.assertEqual(verify_dispatch_window(0,12,previous=10,clock=lambda:10),10)
  with self.assertRaisesRegex(SplunkHatasi,'zaman payı'):
   verify_dispatch_window(0,12,previous=2,clock=lambda:4.001)
  verify_dispatch_window(0,0,clock=lambda:1000)
 def test_initial_sid_visibility_and_real_errors(self):
  from sandbox import splunk_lab as lab
  responses=[{'sid':'probe'},lab.SplunkHatasi('404 status: Unknown sid'),{'entry':[{'content':{'isDone':True,'resultCount':0}}]},{'fields':[],'results':[]}]
  with patch.object(lab,'istek',side_effect=responses),patch.object(lab.time,'sleep') as sleep:
   result=lab.Lab().calistir('pafta_probe',0)
  self.assertEqual(result[0],'probe')
  sleep.assert_called_once_with(0.2)
  with patch.object(lab,'istek',side_effect=[{'sid':'probe'},lab.SplunkHatasi('401 unauthorized')]),self.assertRaisesRegex(lab.SplunkHatasi,'401'):
   lab.Lab().calistir('pafta_probe',0)
 def test_search_time_does_not_extend_interval(self):
  now=[0];waits=[]
  def sleep(seconds):waits.append(seconds);now[0]+=seconds
  clock=lambda:now[0]
  first=dispatch_after(None,12,clock,sleep)
  now[0]+=3
  second=dispatch_after(first,12,clock,sleep)
  now[0]+=4
  third=dispatch_after(second,12,clock,sleep)
  self.assertEqual((first,second,third),(0,12,24))
  self.assertEqual(waits,[9,8])
 def test_overrun_never_adds_an_extra_interval(self):
  now=[21];waits=[]
  with self.assertRaisesRegex(SplunkHatasi,'dispatch aralığı'):
   dispatch_after(0,12,lambda:now[0],waits.append)
  self.assertEqual(waits,[])

def native(repeat):
 from engine.lessons import Library
 from engine.runners import get,for_step
 from sandbox import splunk_lab
 from unittest.mock import patch
 if not splunk_lab._api_acik():raise RuntimeError('Existing Splunk API must already be ready')
 steps=[s for s in Library().lesson('spl','sp22')['steps'] if s['kind']=='tahmin']
 expected=[]
 for iteration in range(repeat):
  for i,s in enumerate(steps):
   # Prevent a missing runtime from triggering image download/start.
   with patch('sandbox.splunk_lab.hazirla',return_value=None):
    r=for_step(get('spl'),s).run(s['code'],s.get('stdin',''),s.get('setup'))
   if r['status']!='ok':raise AssertionError(r)
   output=''.join(v for k,v in r['segs'] if k=='out')
   rows=[line.split('|') for line in output.splitlines()]
   fired=[(r[1],r[5],r[6]) for r in rows]
   if iteration==0:expected.append(fired)
   elif fired!=expected[i]:raise AssertionError((iteration,i,expected[i],fired))
   if i==0:
    assert sum(int(r[5]) for r in rows)==1,output
   else:
    assert [int(r[5]) for r in rows]==[1,0,1],output
   print(f'SP22 prediction {i+1} run {iteration+1}: {fired}',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',action='store_true');p.add_argument('--repeat',type=int,default=8);args=p.parse_args()
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Timing))
 if not r.wasSuccessful():sys.exit(1)
 if args.native:native(args.repeat)
