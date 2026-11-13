"""AD curriculum boundaries, predictions, mutations and opt-in real VM checks."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get,for_step

ANSWERS={
 'ad13':'deny|mehmet.yilmaz|WriteDacl\nallow|SOC-Analistleri|WriteDacl\n',
 'ad14':'Sunucu-Operatorleri\nAltyapi-Yoneticileri\nDomain Admins\n',
 'ad16':'MSSQLSvc/sql01.pafta.local:1433\nsvc_on\n',
 'ad17':'S4U2Self 0x0\nS4U2Proxy 0xD\n',
 'ad19':'LegacyClient False\nWebServer False\nManagerApproved True\n',
 'ad20':'False True\n',
}
MUTATIONS=[
 ('ad13','if ace["tur"] == "deny" and not verildi:','if False:','ignore deny'),
 ('ad13','and not engelli:',':','allow after deny'),
 ('ad13','verildi = kisi == nesne["owner"] and','verildi = False and','ignore owner'),
 ('ad13','veri["gruplar"].get(bekleyen.pop(), [])','veri["gruplar"].get(bekleyen.pop(), [])[:0]','ignore memberships'),
 ('ad13','if ace.get("inherit_only") or ace["kim"] not in token:','if ace["kim"] not in token:','inherit-only'),
 ('ad13','for ace in nesne["aces"]:','for ace in reversed(nesne["aces"]):','reverse ACE order'),
 ('ad13','"GenericAll" in ace["haklar"]','False','ignore GenericAll'),
 ('ad14','for ozne, nesne, _hak in hak_kenarlari:','for ozne, nesne, _hak in []:','drop ACL edges'),
 ('ad14','komsular = {ad: list(ustler) for ad, ustler in gruplar.items()}','komsular = {}','drop membership edges'),
 ('ad14','komsular.setdefault(ozne, []).append(nesne)','komsular.setdefault(nesne, []).append(ozne)','reverse direction'),
 ('ad14','kuyruk.popleft()','kuyruk.pop()','DFS instead of BFS'),
 ('ad16','if hesap["spn"]:','if True:','missing SPN'),
 ('ad16','if spn:','if True:','empty target'),
 ('ad16','for ad in kaynak["allowed_to_act"]:','for ad in []:','drop RBCD'),
 ('ad16','if ad in hesaplar and hesaplar[ad]["spn"]:','if True:','unknown front account'),
 ('ad16','return sorted(sonuc)','return []','empty findings'),
 ('ad17','len(selfler) != 1','len(selfler) < 1','duplicate Self'),
 ('ad17','a["durum"] == b["durum"] == "0x0"','b["durum"] == "0x0"','failed Self'),
 ('ad17','a["durum"] == b["durum"] == "0x0"','a["durum"] == "0x0"','failed Proxy'),
 ('ad17','a["on_hizmet"] == b["on_hizmet"]','True','different service'),
 ('ad17','a["kullanici"] == b["kullanici"]','True','different user'),
 ('ad17','a["sira"] < b["sira"]','a["sira"] <= b["sira"]','equal boundary'),
 ('ad17','b.get("evidence_sira") == a["sira"]','True','wrong evidence'),
 ('ad17','hesap.get("spn") == a["hedef_spn"]','True','wrong Self SPN'),
 ('ad19','t["name_flags"] & 1','t["name_flags"] == 1','subject combined bits'),
 ('ad19','t["name_flags"] & 65536','t["name_flags"] & 65535','SAN boundary'),
 ('ad19','t["enrollment_flags"] & 2','t["enrollment_flags"] == 2','pending combined bits'),
 ('ad19','t["ra_signatures"],','0,','signature count'),
 ('ad19','"1.3.6.1.5.5.7.3.2" in t["eku"]','bool(t["eku"])','serverAuth is not clientAuth'),
 ('ad20','t["published"] and','True and','unpublished template'),
 ('ad20','grup in t["enroll_effective"]','True','no enrollment'),
 ('ad20','"1.3.6.1.5.5.7.3.2" in t["eku"]','True','wrong EKU'),
 ('ad20','t["name_flags"] & 1','bool(t["name_flags"])','neighbor subject bit'),
 ('ad20','not t["enrollment_flags"] & 2','True','manager approval'),
 ('ad20','t["ra_signatures"] == 0','t["ra_signatures"] <= 1','one signature boundary'),
 ('ad20','if grup in t["edit_effective"]:','if False:','drop edit rights'),
]

if os.environ.get('PAFTA_AD_LIVE')=='1':
 ANSWERS.update({
  'ad15':'True\nFalse\n',
  'ad18':'False\n',
  'ad21':'True\nFalse\n',
  'ad22':'bad-ca False\nbad-name False\nstarttls True\n',
  'ad23':'valid True\nnone False\nwrong False\n',
 })
 MUTATIONS.extend([
  ('ad15',"if(Test-PaftaWriteDacl $kisi)","if($kisi -eq 'ali.kaya')",'hardcoded ACL decision'),
  ('ad18','$result.ok',"($mode -in @('classic','rbcd'))",'hardcoded S4U outcome'),
  ('ad21',"$t.'msPKI-Enrollment-Flag' -band 2","$t.'msPKI-Enrollment-Flag' -eq 2",'live combined pending bits'),
  ('ad21',"$t.'msPKI-Certificate-Name-Flag' -band 1","$t.'msPKI-Certificate-Name-Flag' -eq 1",'live combined subject bits'),
  ('ad21','$r.disposition',"$(if($r.disposition -eq 5){3}else{$r.disposition})",'collapse pending into issued'),
  ('ad22','escapes.get(ch, ch)','ch','missing RFC4515 escaping'),
  ('ad22','ad in result.get("names", [])','bool(result.get("names", []))','any result is not exact account'),
  ('ad23','if result["ok"]:','if False:','ignore successful bind'),
  ('ad23','== "certificate"','== "ldap"','swap certificate and bind errors'),
  ('ad23','return "tasima"','return "ldap-bind"','unknown transport boundary'),
 ])



class Curriculum(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  lib=Library()
  cls.lessons={lid:lib.lesson('ad',lid) for lid in ANSWERS}

 def test_predictions(self):
  for lid,lesson in self.lessons.items():
   for step in lesson['steps']:
    if step['kind']!='tahmin':continue
    with self.subTest(lesson=lid,step=step['title']):
     result=for_step(get('ad'),step).run(step['code'])
     self.assertEqual(result['status'],'ok',result)
     self.assertEqual(''.join(v for k,v in result['segs'] if k=='out'),ANSWERS[lid])

 def test_tasks(self):
  for lid,lesson in self.lessons.items():
   for step in lesson['steps']:
    if step['kind']!='gorev':continue
    with self.subTest(lesson=lid,step=step['title']):
     runner=for_step(get('ad'),step)
     self.assertEqual(runner.test(step['solution'],step)['status'],'pass')
     self.assertEqual(runner.test(step['starter'],step)['status'],'fail')

 def test_mutations(self):
  def run(case):
   lid,old,new,name=case
   step=next((s for s in self.lessons[lid]['steps'] if s['kind']=='gorev' and old in s['solution']), None)
   if step is None:
    return lid,name,{'status':'missing mutation','old':old}
   if old not in step['solution']:
    return lid,name,{'status':'missing mutation','old':old}
   return lid,name,for_step(get('ad'),step).test(step['solution'].replace(old,new,1),step)
  with ThreadPoolExecutor(max_workers=1 if os.environ.get('PAFTA_AD_LIVE')=='1' else 2) as pool:
   for lid,name,result in pool.map(run,MUTATIONS):
    with self.subTest(lesson=lid,mutation=name):
     self.assertEqual(result['status'],'fail',result)

 def test_utf8_lf(self):
  for lid in ANSWERS:
   path=next((ROOT/'tracks/ad/lessons').glob(lid+'-*.md'))
   data=path.read_bytes()
   self.assertNotIn(b'\r',data,path)
   data.decode('utf8')


if __name__=='__main__':
 unittest.main()
