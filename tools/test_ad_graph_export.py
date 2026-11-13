"""Official SharpHound data reading: native lesson and semantic mutation checks."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get
MUTANTS=[
 ('reverse membership','ekle(uye["ObjectIdentifier"],hedef,"MemberOf",None)','ekle(hedef,uye["ObjectIdentifier"],"MemberOf",None)'),
 ('reverse ACL','ekle(ace["PrincipalSID"],hedef,ace["RightName"],ace["IsInherited"])','ekle(hedef,ace["PrincipalSID"],ace["RightName"],ace["IsInherited"])'),
 ('ignore primary group','elif nesne.get("PrimaryGroupSID"):','elif False:'),
 ('include deleted endpoints','if kaynak not in silinen and hedef not in silinen:','if True:'),
 ('discard inherited ACL flag','hedef,ace["RightName"],ace["IsInherited"])','hedef,ace["RightName"],False)'),
 ('accept string boolean','if type(ace["IsInherited"]) is not bool:','if False:'),
 ('all rights treated as valid','if ace["RightName"] not in ("GenericAll","WriteDacl"): continue','if False: continue'),
 ('drop GenericAll','("GenericAll","WriteDacl")','("WriteDacl",)'),
 ('use display name identity','hedef=nesne["ObjectIdentifier"]','hedef=nesne["Properties"]["name"]'),
 ('no version check','meta.get("version") != 6','False'),
 ('DFS instead of BFS','kuyruk.popleft()','kuyruk.pop()'),
 ('drop all edges','return sorted(kenarlar,','return sorted(set(),'),
 ('empty path always','if son==hedef:return yol','if son==hedef:return []')]

def main():
 st=next(s for s in Library().lesson('ad','ad14')['steps'] if s['kind']=='gorev' and s['title'].startswith('SharpHound'))
 r=for_step(get('ad'),st);base=r.test(st['solution'],st)
 assert base['status']=='pass',base
 assert r.test(st['starter'],st)['status']=='fail'
 cases=[]
 for name,old,new in MUTANTS:
  assert old in st['solution'],name
  result=r.test(st['solution'].replace(old,new,1),st)
  assert result['status']=='fail',(name,result)
  assert not result.get('error') or result['error']['type'] in ('ValueError',),(name,result)
  cases.append({'name':name,'status':result['status'],'rejected':True})
  print(name+': rejected',flush=True)
 path=ROOT/'tracks/ad/lessons/ad14-acl-erisim-yolu.md'
 result={'reference':'pass','starter':'fail','mutants':cases,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'data_manifest':'tracks/ad/veri/bloodhound/manifest.json','scope':'Official exported sample, read offline; NOT live BloodHound CE UI or DC AccessCheck. Author acceptance, independent rerun pending.'}
 (ROOT/'outputs/laptop-partials-ad60-acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print('reference pass; 13 semantic mutants rejected')
if __name__=='__main__':main()
