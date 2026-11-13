"""Mutate the advanced tasks and run their actual hidden tests on Elastic.
No source-string assertion is substituted for product execution.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get
from tools.audit_elastic_mutations import mutations

def candidates(code,mode):
    seen={code}
    def emit(label,value):
        if value not in seen:
            seen.add(value)
            return label,value
    if mode in ('ingest','rule'):
        obj=json.loads(code)
        variants=[]
        if mode=='ingest':
            for i,p in enumerate(obj['processors']):
                altered=copy.deepcopy(obj);altered['processors'].pop(i)
                variants.append(('processor removed '+str(i),altered))
                name=next(iter(p))
                if name=='convert':
                    for typ in ('integer','long','float'):
                        altered=copy.deepcopy(obj);altered['processors'][i][name]['type']=typ
                        variants.append(('convert '+str(i)+' -> '+typ,altered))
                if name=='set':
                    altered=copy.deepcopy(obj);altered['processors'][i][name]['value']='yanlis'
                    variants.append(('set wrong value '+str(i),altered))
                if name=='date':
                    altered=copy.deepcopy(obj);altered['processors'][i][name]['formats']=['UNIX']
                    variants.append(('date format UNIX',altered))
            if 'on_failure' in obj:
                altered=copy.deepcopy(obj);altered.pop('on_failure')
                variants.append(('on_failure removed',altered))
        else:
            language='eql' if obj.get('language')=='eql' else 'kibana'
            for label,query in mutations(obj['query'],language):
                altered=copy.deepcopy(obj);altered['query']=query
                variants.append(('query '+label,altered))
            for key,value in [('interval','2m'),('from','now-1m'),('to','now-1m')]:
                altered=copy.deepcopy(obj);altered[key]=value
                variants.append((key+' changed',altered))
            if 'threshold' in obj:
                for n in (2,4):
                    altered=copy.deepcopy(obj);altered['threshold']['value']=n
                    variants.append(('threshold '+str(n),altered))
                altered=copy.deepcopy(obj);altered['threshold']['field']=[]
                variants.append(('group removed',altered))
        for label,altered in variants:
            result=emit(label,json.dumps(altered,ensure_ascii=False,indent=2))
            if result:
                yield result
        return
    for label,value in mutations(code,'eql' if mode=='eql' else 'kibana'):
        result=emit(label,value)
        if result:
            yield result
    variants=[]
    if mode=='eql':
        for old,new in [('endsWith~','endsWith'),('between~','between'),('endsWith~','stringContains~')]:
            if old in code:
                variants.append((old+' -> '+new,code.replace(old,new)))
        if '![' in code:
            variants.append(('missing -> positive',code.replace('![','[')))
    if mode=='esql':
        for old,new in [('COUNT(*)','COUNT(bytes)'),('SUM(bytes)','MAX(bytes)'),('1024.0','1024'),('COALESCE(user.name, "bilinmiyor")','user.name')]:
            if old in code:
                variants.append((old+' -> '+new,code.replace(old,new)))
        m=re.search(r'\| SORT [^|]+',code)
        if m:
            variants.append(('SORT removed',code[:m.start()]+code[m.end():]))
        m=re.search(r'\| KEEP [^|]+',code)
        if m:
            variants.append(('KEEP removed',code[:m.start()]+code[m.end():]))
    for label,value in variants:
        result=emit(label,value)
        if result:
            yield result

def main():
    lib=Library();jobs=[];tasks=[]
    for lid in lib.outline('elastic')['order']:
        for index,step in enumerate(lib.lesson('elastic',lid)['steps']):
            if step['kind']!='gorev' or json.loads(step.get('stdin','{}')).get('backend')!='elastic':
                continue
            mode=step['meta']['dil'];tasks.append((lid+':'+str(index),step))
            for label,code in candidates(step['solution'],mode):
                jobs.append((lid,index,step,label,code))
    def check(job):
        lid,index,step,label,code=job
        result=get('elastic').test(code,step)
        # With no BY, STATS emits exactly its declared aggregate columns in
        # declaration order. This KEEP retains every such column in that order;
        # removing only that projection cannot affect rows, types, or order.
        equivalent=None
        if label=='KEEP removed' and re.search(r'\| STATS adet = COUNT\(\*\), toplam_kib = SUM\(kib\) \| KEEP adet, toplam_kib\s*$',step['solution']):
            equivalent='STATS without BY already exposes exactly adet, toplam_kib in this order; identity KEEP projection.'
        return {'lesson':lid,'step':index,'label':label,'code':code,'status':result['status'],'equivalence_reason':equivalent,
                'checks':[c for c in result.get('checks',[]) if not c['ok']], 'error':result.get('error')}
    results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        controls=list(pool.map(lambda item:(item[0],get('elastic').test(item[1]['solution'],item[1])),tasks))
    invalid=[(name,r) for name,r in controls if r['status']!='pass']
    if invalid:
        for name,r in invalid:
            print('ORIGINAL FAILED',name,r,flush=True)
        return 1
    print('16 özgün çözüm kontrolü temiz; mutasyonlar başlıyor.',flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(check,job) for job in jobs]):
            item=future.result();results.append(item)
            if item['status']=='pass' and not item['equivalence_reason']:
                print('SURVIVED',item['lesson'],item['step'],item['label'],flush=True)
            if len(results)%20==0:
                print(len(results),'/',len(jobs),flush=True)
    results.sort(key=lambda r:(r['lesson'],r['step'],r['label']))
    survived=[r for r in results if r['status']=='pass' and not r['equivalence_reason']]
    equivalents=[r for r in results if r['status']=='pass' and r['equivalence_reason']]
    infrastructure=[r for r in results if r['status'] in ('timeout','internal')]
    report={'version':'9.5.5','tasks':len(tasks),'baseline_pass':len(controls)-len(invalid),
            'mutations':len(results),'survived':len(survived),'equivalent':len(equivalents),
            'infrastructure_errors':len(infrastructure),'results':results}
    (ROOT/'outputs'/'codex-elastic-native-mutations.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    print('Tasks',len(tasks),'mutations',len(results),'survived',len(survived),flush=True)
    return bool(survived or infrastructure)

if __name__=='__main__':
    sys.exit(main())
