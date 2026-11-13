"""Validation and negative submissions for the 48 authorized new lessons."""
import ast,json,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get
OUT=ROOT/'outputs/ai-ctf-olay-20261110';OUT.mkdir(parents=True,exist_ok=True)
lib=Library();runner=get('python')
ids={'ai-ctf':range(1,11),'ai-olay':range(1,17),'ai-bulut':range(1,9),'ai-ile-guvenlik':range(21,26),'ai-guvence':[51],'kuantum':range(21,29)}
jobs=[];manifest=[]
class Invert(ast.NodeTransformer):
 def __init__(self):self.changed=False
 def visit_Compare(self,node):
  if not self.changed:
   mapping={ast.Eq:ast.NotEq,ast.NotEq:ast.Eq,ast.Lt:ast.GtE,ast.Gt:ast.LtE,ast.LtE:ast.Gt,ast.GtE:ast.Lt,ast.In:ast.NotIn,ast.NotIn:ast.In,ast.Is:ast.IsNot,ast.IsNot:ast.Is}
   if type(node.ops[0]) in mapping:node.ops[0]=mapping[type(node.ops[0])]();self.changed=True
  return self.generic_visit(node)
for tid,nums in ids.items():
 for n in nums:
  lid=f'{tid}-{n:02}';lesson=lib.lesson(tid,lid);assert lesson,lid
  tasks=[s for s in lesson['steps'] if s['kind']=='gorev']
  manifest.append({'track':tid,'lesson':lid,'title':lesson['title'],'tasks':len(tasks),'steps':len(lesson['steps'])})
  for i,step in enumerate(tasks,1):
   tree=ast.parse(step['test']);name=next(node.args[0].value for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='need')
   fixed=None
   for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='eq' and len(node.args)>1:
     try:fixed=ast.literal_eval(node.args[1]);break
     except Exception:pass
   prefix=f'{lid}/{i}'
   jobs.append((prefix,'empty','',step))
   jobs.append((prefix,'memorized-first-result',f'def {name}(*args,**kwargs):\n    return {fixed!r}',step))
   source=ast.parse(step['solution']);target=next((f for f in source.body if isinstance(f,ast.FunctionDef) and f.name==name),None)
   if target:
    mut=Invert();mut.visit(target)
    if mut.changed:jobs.append((prefix,'inverted-boundary',ast.unparse(source),step))
   if tid=='ai-ctf' and i==1:
    # Wrong lesson solutions must fail even when their function name is adapted.
    other_n=n+1 if n<10 else 1
    other_step=next(s for s in lib.lesson(tid,f'ai-ctf-{other_n:02}')['steps'] if s['kind']=='gorev')
    other=other_step['solution'].replace(f'bayrak_al_{other_n}',name)
    jobs.append((prefix,'wrong-target-solution',other,step))
   if tid=='ai-ctf' and i==2:
    for value in (True,False):jobs.append((prefix,'allow-all' if value else 'deny-all',f'def {name}(*args,**kwargs):\n    return {value!r}',step))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
def run(job):
 label,kind,code,step=job
 start=time.monotonic();result=runner.test(code,step)
 return {'task':label,'mutant':kind,'rejected':result['status'] in ('fail','error'),'status':result['status'],'seconds':round(time.monotonic()-start,3)}
results=[]
with ThreadPoolExecutor(max_workers=4) as pool:
 for i,res in enumerate(pool.map(run,jobs),1):
  results.append(res)
  if not res['rejected']:print('SURVIVOR',res,flush=True)
  if i%30==0:print(f'checked {i}/{len(jobs)}',flush=True)
report={'lessons':len(manifest),'tasks':sum(m['tasks'] for m in manifest),'negative_submissions':len(results),'rejected':sum(r['rejected'] for r in results),'results':results}
(OUT/'negative-submissions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
