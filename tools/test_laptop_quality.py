"""Laptop repair acceptance: references and deliberately wrong quality solutions.

Runs real Pafta runners. Does not install packages or change scores.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get

SPECS={
 'pu14':[
 ('wrong gateway','if str(v).split(";", 1)[0].strip().casefold() == guvenilen_authserv.strip().casefold()]','if True]'),
 ('allow duplicate trusted result','len(secilen) > 1','len(secilen) > 2'),
 ('constant raw hash','hashlib.sha256(ham)','hashlib.sha256(b"")'),
 ('omit missing auth finding','if not secilen:','if False:'),
 ('invert Received check','["stage_received_index"] is None','["stage_received_index"] is not None'),
 ('omit attachment findings','bulgular.update(ek["findings"])','pass'),
 ('omit attachment hashes','[e["sha256"] for e in ekler]','[]'),
 ('omit URL mismatch','if bag["uyusmuyor"]:','if False:'),
 ('omit URL userinfo','if bag["kullanici_bilgisi"]:','if False:'),
 ('claim whole campaign coverage','yalniz-bu-ileti; alici-kapsami-izleme-kaydiyla-dogrulanmadi','kampanya-tumu-dogrulandi')],
 'pu17':[
 ('assume NTLM without provenance','kaynak != "windows-ntds"','False'),
 ('accept NTDS/bcrypt mismatch','kaynak == "windows-ntds" and tur != "ntlm"','False'),
 ('wrong cost boundary','p["cost"] < minimum_bcrypt_cost','p["cost"] <= minimum_bcrypt_cost'),
 ('ignore caller threshold','p["cost"] < minimum_bcrypt_cost','p["cost"] < 12'),
 ('claim password known','"parola_dogrulandi": False','"parola_dogrulandi": True'),
 ('leak parsed hash','"parametreler": params','"parametreler": p'),
 ('lose work parameters','"parametreler": params','"parametreler": {}'),
 ('lose yescrypt verification warning','if tur == "yescrypt":','if False:'),
 ('reject min valid threshold','4 <= minimum_bcrypt_cost','4 < minimum_bcrypt_cost'),
 ('reject max valid threshold','minimum_bcrypt_cost <= 31','minimum_bcrypt_cost < 31')]
}

def main():
 lib=Library();report={"scope":"Author self-acceptance; independent auditor rerun required", "lessons":{}}
 for lid,mutants in SPECS.items():
  step=next(s for s in lib.lesson('purple',lid)['steps'] if s['kind']=='gorev' and s['title'].startswith('4 ·'))
  runner=for_step(get('purple'),step)
  result=runner.test(step['solution'],step)
  assert result['status']=='pass',(lid,'reference',result)
  records=[]
  for name,old,new in mutants:
   assert old in step['solution'],(lid,name)
   result=runner.test(step['solution'].replace(old,new),step)
   assert result['status']=='fail',(lid,name,result)
   assert result.get('error') is None or result['error']['type'] in ('ValueError',),(lid,name,result)
   records.append({"case":name,"rejected":True,"status":result['status']})
  report['lessons'][lid]={"reference":"pass","starter":runner.test(step['starter'],step)['status'],"wrong_solutions":records}
  print(lid+': reference pass, '+str(len(records))+' deliberately wrong solutions rejected',flush=True)
 for lid in SPECS:
  path=next((ROOT/'tracks/purple/lessons').glob(lid+'*'))
  report['lessons'][lid]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
 out=ROOT/'outputs/laptop-20261027-purple-acceptance.json'
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(out)

if __name__=='__main__':main()
