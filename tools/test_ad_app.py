"""AD HTTP routing and disposable progress, including opt-in managed guests."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server
from engine.lessons import Library


class AdApp(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory(prefix='pafta_ad_api_')
  self.addCleanup(self.folder.cleanup)
  env=patch.dict(os.environ,{'PAFTA_DATA':self.folder.name})
  env.start();self.addCleanup(env.stop)
  self.app,self.httpd=server.start(0,token='ad-api-local-test')
  self.addCleanup(self.httpd.server_close)
  self.addCleanup(self.httpd.shutdown)
  self.lib=Library()

 def api(self,path,body=None):
  request=Request(f'http://127.0.0.1:{self.app.port}'+path,
   data=json.dumps(body).encode() if body is not None else None,
   headers={'X-Pafta-Token':'ad-api-local-test','Content-Type':'application/json'})
  with urlopen(request,timeout=260) as response:return json.load(response)

 def test_outline_offline_check_guess_and_private_tests(self):
  track=self.api('/api/track/ad')['track']
  ids=[s['id'] for m in track['modules'] for s in m['lessons']]
  self.assertEqual(ids,[f'ad{i:02}' for i in range(1,26)])
  self.assertEqual(len(track['ranks']),6)
  lesson=self.lib.lesson('ad','ad16')
  public=self.api('/api/lesson/ad/ad16')['lesson']
  self.assertTrue(all('test' not in s and 'solution' not in s for s in public['steps']))
  i,task=next((i,s) for i,s in enumerate(lesson['steps']) if s['kind']=='gorev')
  body={'track':'ad','lesson':'ad16','step':i}
  self.assertEqual(self.api('/api/check',dict(body,code=task['solution']))['status'],'pass')
  i=next(i for i,s in enumerate(lesson['steps']) if s['kind']=='tahmin')
  self.assertTrue(self.api('/api/guess',{'track':'ad','lesson':'ad16','step':i,
   'guess':'MSSQLSvc/sql01.pafta.local:1433\nsvc_on'})['correct'])
  self.assertTrue(Path(self.folder.name,'progress.json').exists())

 @unittest.skipUnless(os.environ.get('PAFTA_AD_LIVE')=='1','set PAFTA_AD_LIVE=1')
 def test_run_routes_to_real_guest_and_real_ldap(self):
  for lid,source,expected in [
   ('ad15','$env:COMPUTERNAME','PF-DC01'),
   ('ad22',"from ad_lab import probe\nprint(probe('valid')['ok'])",'True')]:
   lesson=self.lib.lesson('ad',lid)
   i=next(i for i,s in enumerate(lesson['steps']) if s['kind']=='gorev')
   result=self.api('/api/run',{'track':'ad','lesson':lid,'step':i,'code':source})
   self.assertEqual(result['status'],'ok',result)
   self.assertEqual(''.join(v for k,v in result['segs'] if k=='out').strip(),expected)


if __name__=='__main__':unittest.main()
