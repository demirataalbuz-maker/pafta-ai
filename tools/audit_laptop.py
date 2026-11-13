"""Read-only lesson execution audit. Reports declarations and blocked runtimes separately.

Uses the repository's job generator, but never treats an unavailable starter or
an author-supplied prediction output as a successful runtime measurement.
"""
import argparse,collections,concurrent.futures,datetime,hashlib,json,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
import validate as V
from engine.lessons import Library
from engine.runners import get,for_step,argv_coz

BLOCK_TYPES={'ADLaboratuvarı','PostgreSQLYok','MariaDBYok','SplunkYok','WSL','VQLHatası'}
BLOCK_WORDS=('CIM 8.5.0','CIM arşivi','imajı yok','imaj yok','Docker Desktop','laboratuvarı kurulmamış','VMware bulunamadı','JDK 17+','model bulunamadı')

def classify(kind,r,body=''):
 status=r.get('status');err=r.get('error') or {};typ=err.get('type','');msg=err.get('msg','')
 if typ in BLOCK_TYPES or any(w.casefold() in (msg+' '+r.get('detail','')).casefold() for w in BLOCK_WORDS):return 'BLOCKED'
 if typ=='SplunkHatası' and (re.search(r"Data model '(?:Authentication|Web|Network_Traffic|Endpoint|Change)' was not found",msg) or re.search(r"macro '(?:drop_dm_object_name|cim_(?:Authentication|Web|Network_Traffic|Endpoint|Change)_indexes)' that cannot be found",msg)):return 'BLOCKED'
 if status in ('internal','timeout','cancelled'):return 'ERROR'
 if kind=='starter':
  if status=='pass':return 'FAIL'
  if status=='fail' and any(not c.get('ok') for c in r.get('checks',[])):return 'PASS'
  if status=='fail' and err and err.get('where') not in ('kod','kod-test'):return 'ERROR'
  if status=='fail':return 'PASS'
  if status=='error' and err.get('where') in ('kod','kod-test') and typ not in ('FileNotFoundError','ModuleNotFoundError'):return 'PASS'
  return 'ERROR'
 if kind=='solution':return 'PASS' if status=='pass' else 'FAIL'
 if status=='ok':return 'PASS'
 if status=='error' and kind=='tahmin' and 'hata' in body.lower():return 'PASS'
 return 'FAIL'

def execute(job,runner_name):
 kind,tid,where,st,code=job;start=time.monotonic()
 record={'kind':kind,'where':where,'lesson':where.split(':',1)[0].split('/')[-1]}
 if st is None:return dict(record,status='FAIL',detail='Lesson structure: '+kind)
 if kind=='tahmin' and st.get('gercek') is not None:return dict(record,status='DECLARED',detail='Author-supplied output; not executed by this runner')
 try:
  runner=for_step(get(runner_name),st)
  if kind in ('solution','starter'):r=runner.test(code,st)
  else:r=runner.run(code,st.get('stdin',''),st.get('setup'),argv=argv_coz(st.get('meta')))
  record.update(status=classify(kind,r,st.get('body','')),runner=runner.name,runner_status=r.get('status'),seconds=round(time.monotonic()-start,3))
  if r.get('error'):record['error']=r['error']
  if r.get('detail'):record['detail']=str(r['detail'])[-1200:]
  checks=r.get('checks',[]);record['checks_passed']=sum(bool(c.get('ok')) for c in checks)
  record['failed_checks']=[c for c in checks if not c.get('ok')][:3]
 except Exception as e:record.update(status='ERROR',detail=type(e).__name__+': '+str(e)[:800])
 return record

def main():
 from engine.runtime_env import refresh_windows_runtime_env
 refresh_windows_runtime_env()
 p=argparse.ArgumentParser();p.add_argument('--track',required=True);p.add_argument('--output',required=True);p.add_argument('--shell-label',required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
 lib=Library();t=lib.track(a.track);ids=lib.outline(a.track)['order'];jobs=[]
 for lid in ids:jobs.extend(V.jobs_for(lib,a.track,t.get('dil',a.track),lid))
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 result={'track':a.track,'shell':a.shell_label,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lessons':list(ids),'scope':'Automated reference/starter/example execution, not independent quality scoring or live portal acceptance','results':[]}
 ledger=out.with_suffix('.jsonl')
 with ledger.open('w',encoding='utf8') as f,concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  futures=[pool.submit(execute,j,t.get('runner',a.track)) for j in jobs]
  for fut in concurrent.futures.as_completed(futures):
   r=fut.result();result['results'].append(r);f.write(json.dumps(r,ensure_ascii=False,default=str)+'\n');f.flush()
 issues,coverage=V.kazanim_denetle(lib,a.track);result['curriculum_errors']=issues;result['curriculum_coverage']=coverage
 result['counts']=dict(collections.Counter(r['status'] for r in result['results']))
 result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 result['source_sha256']={str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'tracks'/a.track/'lessons').glob('*.md')}
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')
 print(a.track,json.dumps(result['counts']),flush=True)
 return 1 if any(result['counts'].get(x) for x in ('FAIL','ERROR','BLOCKED')) or issues else 0
if __name__=='__main__':sys.exit(main())
