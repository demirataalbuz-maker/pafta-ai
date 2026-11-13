"""Collate measured attempts without turning skips/timeouts into a pass."""
import collections,datetime,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'outputs/audit-20261027'
def main():
 attempts=[]
 for folder in ('regressions','extra','retries','long-retries'):
  path=BASE/folder/'summary.json'
  if path.exists():attempts.extend(json.loads(path.read_text(encoding='utf8')))
 manual=BASE/'manual-regression-attempts.json'
 if manual.exists():attempts.extend(json.loads(manual.read_text(encoding='utf8')))
 grouped=collections.defaultdict(list)
 for attempt in attempts:
  a=dict(attempt);path=ROOT/a['log'];text=path.read_text(encoding='utf-8-sig',errors='replace') if path.exists() else ''
  ran=re.findall(r'Ran (\d+) tests?',text);skipped=re.findall(r'skipped=(\d+)',text)
  a['unit_tests']=int(ran[-1]) if ran else None;a['skipped_tests']=int(skipped[-1]) if skipped else 0
  if a['exit']==124:a['status']='TIMEOUT'
  elif a['exit'] and 'ADLaboratuvarı' in text:a['status']='BLOCKED'
  elif a['exit']:a['status']='FAIL'
  elif a['unit_tests'] is not None and a['unit_tests']==a['skipped_tests']:a['status']='SKIPPED'
  else:a['status']='PASS'
  if not path.exists():a['status']='UNTESTED'
  a['log_sha256']=__import__('hashlib').sha256(path.read_bytes()).hexdigest() if path.exists() else None
  a['observed_mtime']=path.stat().st_mtime if path.exists() else 0;grouped[a['name']].append(a)
 suites=[]
 for name,values in sorted(grouped.items()):
  ordered=sorted(values,key=lambda x:x['observed_mtime']);last=ordered[-1]
  suites.append({'name':name,'status':last['status'],'latest':last,'attempts':ordered})
 result={'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Selected application/runtime/security regression suites plus targeted acceptance. Does not claim every optional test file was run or unavailable live labs passed.','suite_count':len(suites),'counts':dict(collections.Counter(s['status'] for s in suites)),'unit_tests_in_latest_suites':sum(s['latest']['unit_tests'] or 0 for s in suites),'skipped_tests_in_latest_suites':sum(s['latest']['skipped_tests'] for s in suites),'suites':suites}
 (BASE/'regression-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:result[k] for k in ('suite_count','counts','unit_tests_in_latest_suites','skipped_tests_in_latest_suites')},ensure_ascii=False))
if __name__=='__main__':main()
