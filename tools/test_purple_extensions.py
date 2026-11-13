"""Execute six predictions and reject boundary/meaning mutations in PU04–09."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get

CASES = [
 ('pu04',0,"return v in (True,1,'1')",'return bool(v)'),
 ('pu04',0,'and not deleted','and True'),
 ('pu04',0,"'domain','ip-dst','sha256'","'domain','ip-dst'"),
 ('pu04',1,'seen<=now','seen<now'),
 ('pu04',1,'now<seen+ttl','now<=seen+ttl'),
 ('pu04',1,"if 'last_seen' in a:",'if False:'),
 ('pu05',0,'.strip().lower().rstrip(\'.\')',".strip().rstrip('.')"),
 ('pu05',0,'{64}','{63,65}'),
 ('pu05',1,'o.ts>=?','o.ts>?'),
 ('pu05',1,'o.ts<?','o.ts<=?'),
 ('pu05',1,'SELECT DISTINCT','SELECT'),
 ('pu05',1,'o.kind=i.kind AND o.value=i.value','o.value=i.value'),
 ('pu06',0,'len(ids)!=len(actions)','False'),
 ('pu06',0,'key=key.lower()','key=key'),
 ('pu06',0,"6:'Warn'","6:'Block'"),
 ('pu06',0,"5:'NotConfigured'","5:'Block'"),
 ('pu06',1,"0<=v.get('age_hours',25)<=24","0<=v.get('age_hours',25)<24"),
 ('pu06',1,"v.get('samples',0)>=100","v.get('samples',0)>100"),
 ('pu06',1,"v.get('critical',1)==0",'True'),
 ('pu07',0,"r.findall('Exceptions/*')","r.findall('Conditions/*')"),
 ('pu07',0,"c.get('EnforcementMode','NotConfigured')","'Enabled'"),
 ('pu07',0,"r.get('Action')","'Allow'"),
 ('pu07',1,"r.get('mode')=='Enabled'",'True'),
 ('pu07',1,"r.get('lab_test_kind')=='enforcement'",'True'),
 ('pu07',1,"r.get('effective_policy') is True",'True'),
 ('pu08',0,"row['eventVersion'].split('.')[0]!='1'",'False'),
 ('pu08',0,'key in seen and seen[key]!=row','False'),
 ('pu08',0,'dt.astimezone(timezone.utc).isoformat()','dt.isoformat()'),
 ('pu08',0,"row.get('errorCode') or 'no-error-recorded'","'no-error-recorded'"),
 ('pu08',1,"'actor':u.get('arn')","'actor':c.get('sessionIssuer',{}).get('arn')"),
 ('pu08',1,"'false':False","'false':True"),
 ('pu09',0,'type(code) is not int','not isinstance(code,int)'),
 ('pu09',0,"code==0","code!=0"),
 ('pu09',1,'0<=delta<=span','0<delta<=span'),
 ('pu09',1,'0<=delta<=span','0<=delta<span'),
 ('pu09',1,"actor!=s['userId']",'False'),
 ('pu09',1,"a.get('result')!='success'",'False'),
 ('pu09',1,'if t.tzinfo is None:', 'if False:'),
]

class PurpleExtensions(unittest.TestCase):
 def test_predictions(self):
  expected = {
   'pu04':'True\nFalse\n', 'pu05':'0\n',
   'pu06':"['Audit', 'Block', 'Warn']\n",
   'pu07':"[('Exe', 'AuditOnly'), ('Script', 'Enabled')]\n",
   'pu08':'AssumedRole\nFalse\n', 'pu09':'True\nFalse\n',
  }
  for lid, output in expected.items():
   step=next(s for s in Library().lesson('purple',lid)['steps'] if s['kind']=='tahmin')
   result=get('purple').run(step['code'])
   self.assertEqual(result['status'],'ok',result)
   self.assertEqual(''.join(v for k,v in result['segs'] if k=='out'),output)

 def test_mutations(self):
  for lid,index,old,new in CASES:
   step=[s for s in Library().lesson('purple',lid)['steps'] if s['kind']=='gorev'][index]
   with self.subTest(lesson=lid,mutation=old):
    self.assertIn(old,step['solution'])
    result=get('purple').test(step['solution'].replace(old,new,1),step)
    self.assertEqual(result['status'],'fail',result)

if __name__=='__main__':
 unittest.main()
