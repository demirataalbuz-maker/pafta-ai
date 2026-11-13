"""Capstone: real predictions, all task boundaries, and shared-engine regression."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get

CASES=[
 ('bt01',0,'bool(manifest)','True'),
 ('bt01',0,'set(manifest)==set(files)','set(manifest)<=set(files)'),
 ('bt01',0,'set(manifest)==set(files)','True'),
 ('bt01',0,'==digest','!=digest'),
 ('bt01',1,'start.tzinfo is None','False'),
 ('bt01',1,"r['source']+':'+r['id']","r['id']"),
 ('bt01',1,'key in seen and seen[key]!=r','False'),
 ('bt01',1,"type(r['ts']) is not int","not isinstance(r['ts'],int)"),
 ('bt01',1,'.astimezone(timezone.utc)',''),
 ('bt02',0,'ts >= 0','ts > 0'),
 ('bt02',0,'ts <= 120','ts < 120'),
 ('bt02',0,'source == "auth" and ',''),
 ('bt02',0,'host == "ws01" and ',''),
 ('bt02',0,'user == "alice" and ',''),
 ('bt02',0,'outcome == "failure" and ',''),
 ('bt02',1,'ts>=0','ts>0'),
 ('bt02',1,'ts<=120','ts<120'),
 ('bt02',1,'source="auth" AND ',''),
 ('bt02',1,'host="ws01" AND ',''),
 ('bt02',1,'user="alice" AND ',''),
 ('bt02',1,'outcome="failure" AND ',''),
 ('bt03',0,'Image|endswith:','Image|contains:'),
 ('bt03',0,'CommandLine|contains:','CommandLine|endswith:'),
 ('bt03',0,'Image|endswith:','Image|endswith|cased:'),
 ('bt03',1,'h=set(hits)','h=set()'),
 ('bt03',1,'len(p-h)','len(p)'),
 ('bt03',1,'h-set(labels)','False'),
 ('bt03',1,'if tp+fp else None','if tp+fp else 1.0'),
 ('bt04',0,'ip.src == 10.0.0.10 and ',''),
 ('bt04',0,'http.host == "updates.lab.test" and ',''),
 ('bt04',0,'http.request.uri == "/health.ps1"','http.request.uri contains "/health.ps1"'),
 ('bt04',1,'if a!=b:','if False:'),
 ('bt04',1,"ep=[r for r in rows if r['source']=='endpoint']",'ep=rows'),
 ('bt04',1,'timeline.update(v.paket_zamanlari(frames))','pass'),
 ('bt04',1,'rows=v.yukle() if rows is None else rows','rows=v.yukle()'),
 ('bt05',0,"c['id'] in result",'False'),
 ('bt05',0,"not c['text'].strip()",'False'),
 ('bt05',0,'not refs<=set(available)','False'),
 ('bt05',0,"(c['kind']=='observed' and not refs)",'False'),
 ('bt05',1,'if any(not v.get(k) for k in required):','if False:'),
 ('bt05',1,"if any(not v['reproduction'].get(k) for k in ('queries','tool_versions','manifest_sha256')):",'if False:'),
 ('bt05',1,'ensure_ascii=False','ensure_ascii=True'),
 ('bt06',0,"if not r.get('refs') or not set(r['refs'])<=set(available):",'if False:'),
 ('bt06',0,'if dt.tzinfo is None:','if False:'),
 ('bt06',0,"not r.get(k,'').strip()",'False'),
 ('bt06',1,'fp>v[\'negatives\']','False'),
 ('bt06',1,'fp<=2','fp<2'),
 ('bt06',1,'tp/(tp+fp)>=0.95','tp/(tp+fp)>0.95'),
 ('bt06',1,"0<=v.get('age_hours',25)<=24","0<v.get('age_hours',25)<=24"),
 ('bt06',1,"0<=v.get('age_hours',25)<=24","0<=v.get('age_hours',25)<24"),
 ('bt06',1,'fn==0','True'),
 ('bt06',1,"v.get('rollback_tested') is True",'True'),
]


class Capstone(unittest.TestCase):
 def test_predictions(self):
  expected={
   'bt01':'True\nFalse\n',
   'bt02':"['a-edge']\n",
   'bt03':"['p-run', 'p-maint', 'p-otherimage']\n3\n",
   'bt04':"[1, 2, 4]\n[(130.0, 'vaka.pcap#frame=1')]\n",
   'bt05':'True\nFalse\n',
   'bt06':'0.95\n1.0\n',
  }
  for lid,output in expected.items():
   step=next(s for s in Library().lesson('bitirme',lid)['steps'] if s['kind']=='tahmin')
   result=get('bitirme').run(step['code'])
   self.assertEqual(result['status'],'ok',result)
   self.assertEqual(''.join(v for k,v in result['segs'] if k=='out'),output)

 def test_mutations(self):
  for lid,index,old,new in CASES:
   step=[s for s in Library().lesson('bitirme',lid)['steps'] if s['kind']=='gorev'][index]
   with self.subTest(lesson=lid,old=old):
    self.assertIn(old,step['solution'])
    result=get('bitirme').test(step['solution'].replace(old,new,1),step)
    self.assertEqual(result['status'],'fail',result)

 def test_adapters(self):
  code='''import vaka_lab as v
from pathlib import Path
import json,hashlib
from sandbox.packet_engine import PacketError
from sandbox import packet_fixtures as f
before={n:Path(n).read_bytes() for n in ('olaylar.jsonl','vaka.pcap','vaka.json','manifest.json')}
manifest=json.loads(before['manifest.json'])
assert all(hashlib.sha256(before[n]).hexdigest()==h for n,h in manifest.items())
assert len(v.yukle())==12
assert v.sorgu('spl','sourcetype=olaylar | where ts=0 | table _time')==[{'_time':1793005200}]
for value in (0,5,True):
    try:v.paket_zamanlari([value])
    except ValueError:pass
    else:raise AssertionError('bad frame accepted')
try:v.sorgu('sql','SELECT 1')
except ValueError:pass
else:raise AssertionError('dialect fallback')
for mode in ('kql','spl'):
    try:v.sorgu(mode,'not_a_supported_command')
    except Exception:pass
    else:raise AssertionError('bad query silently accepted')
try:v.paketler('this is not a valid filter!!!')
except PacketError:pass
else:raise AssertionError('bad filter silently accepted')
frames=[]
for idx,(src,uri,host) in enumerate([('10.0.0.10','/health.ps1','updates.lab.test'),('10.0.0.11','/health.ps1','updates.lab.test'),('10.0.0.10','/health.ps1.bak','updates.lab.test'),('10.0.0.10','/health.ps1','other.lab.test')]):
    dst='198.51.100.80'
    segment=f.tcp(42000+idx,80,f.http_request(uri,host),src=src,dst=dst,flags=0x18)
    frames.append(f.ethernet(f.ipv4(segment,src,dst,6)))
assert f.pcap(frames,start=1793005330)==before['vaka.pcap']
assert all(Path(n).read_bytes()==b for n,b in before.items())
print('native adapters and immutable corpus: OK')
'''
  result=get('bitirme').run(code)
  self.assertEqual(result['status'],'ok',result)

if __name__=='__main__':unittest.main()
