"""PS29 real managed guest / WinRM acceptance and focused mutations."""
import copy
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['PSModulePath']=str(Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/Modules')
from engine.lessons import Library
from engine.runners import for_step,get


def main():
    steps=Library().lesson('powershell','ps29')['steps']
    prediction=next(s for s in steps if s['kind']=='tahmin' and s.get('meta',{}).get('motor')=='ad-vm')
    runner=for_step(get('powershell'),prediction)
    result=runner.run(prediction['code'],'',prediction.get('setup'))
    assert result['status']=='ok',result
    stdout=''.join(value for kind,value in result['segs'] if kind=='out')
    assert stdout=='COMMAND_ERROR\nOpened\n42\n0\n',result
    print('real WinRM prediction: verified',flush=True)
    step=next(s for s in steps if s['kind']=='gorev' and 'WSManConnectionInfo' in s.get('solution',''))
    runner=for_step(get('powershell'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    print('full real WinRM reference: passed',flush=True)
    base_test=step['test'].split("eq(json.loads(out)",1)[0]
    mutations=[
        ('omit session cleanup','Remove-PSSession -Session $s -ErrorAction Stop',"Write-Verbose 'cleanup omitted'",'error',2),
        ('nonpersistent total','$script:total+=$increment','$script:total=$increment','ok',2),
        ('exclusive negative limit','$n -lt -10','$n -le -10','ok',-10),
        ('exclusive positive limit','$n -gt 10','$n -ge 10','ok',10),
        ('broken incorrectly reported closed','after=$s.State.ToString()',"after='Closed'",'broken',0),
        ('command error incorrectly reported broken','$before=$s.State.ToString()',"$before='Broken'",'error',1),
        ('transport error mislabeled',"$handled='transport-error'","$handled='command-error'",'broken',0),
    ]
    records=[]
    for name,old,new,mode,n in mutations:
        assert old in step['solution'],name
        focused=copy.deepcopy(step)
        focused['stdin']=mode+'\n'+str(n)+'\n'
        focused['test']=base_test+f"eq(json.loads(out),expected({mode!r},{n}),{name!r})\n"
        result=runner.test(step['solution'].replace(old,new),focused)
        rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
        assert rejected,(name,result)
        records.append({'mutation':name,'status':'rejected','runner_status':result['status'],'input':focused['stdin']})
        print(name+': rejected',flush=True)
    report={'backend':'real PF-APP01 Windows Server / WSMan localhost',
            'prediction_stdout':stdout,'references_passed':1,'mutants_rejected':len(records),'mutants_passed':0,'cases':records,
            'scope':'Reference uses full lesson tests; mutants use the corresponding original expected(mode,n) predicate with one real guest execution per witness.'}
    (ROOT/'outputs/a-notu-ps29-winrm-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
