"""PS23 real PowerShell 7 HTTP predictions and semantic mutations."""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
# Keep the Windows 5.1 module path independent of the Codex host's bundled PS7.
os.environ['PSModulePath']=str(Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/Modules')
from engine.lessons import Library
from engine.runners import for_step,get


def main():
    steps=Library().lesson('powershell','ps23')['steps']
    prediction=next(s for s in steps if s['kind']=='tahmin' and 'MaximumRedirection' in s.get('code',''))
    result=for_step(get('powershell'),prediction).run(prediction['code'],'',prediction.get('setup'))
    assert result['status']=='ok',result
    stdout=''.join(text for kind,text in result['segs'] if kind=='out')
    assert stdout=='True\n302\n',result
    specifications=[
        ('redirect','-MaximumRedirection 2',[
            ('too few redirects','-MaximumRedirection 2','-MaximumRedirection 1'),
            ('too many redirects','-MaximumRedirection 2','-MaximumRedirection 3'),
            ('exclude zero hops','$n -lt 0','$n -le 0'),
            ('exclude five hops','$n -gt 5','$n -ge 5'),
        ]),
        ('multipart','-Form @{',[
            ('URL-encoded body instead of multipart','-Form @{','-Body @{'),
            ('filename text instead of file bytes','dosya=(Get-Item -LiteralPath $yol)','dosya=$yol'),
            ('fixed note','not=$Girdi[0]','not="a&b=ç"'),
        ]),
        ('timeout','-OperationTimeoutSeconds 1',[
            ('two second budget','-ConnectionTimeoutSeconds 1 -OperationTimeoutSeconds 1','-ConnectionTimeoutSeconds 2 -OperationTimeoutSeconds 2'),
            ('missing body timeout type',' -or $_.Exception -is [System.TimeoutException]',''),
            ('exception types combined with AND','[System.Threading.Tasks.TaskCanceledException] -or $_.Exception','[System.Threading.Tasks.TaskCanceledException] -and $_.Exception'),
            ('HTTP failures mislabeled timeout',"else { throw }","else { 'TIMEOUT' }"),
            ('exclude zero delay','$ms -lt 0','$ms -le 0'),
        ]),
    ]
    records=[]
    for label,marker,mutations in specifications:
        step=next(s for s in steps if s['kind']=='gorev' and marker in s.get('solution',''))
        runner=for_step(get('powershell'),step)
        result=runner.test(step['solution'],step)
        assert result['status']=='pass',(label,'reference',result)
        print(label+': reference passed',flush=True)
        for name,old,new in mutations:
            assert old in step['solution'],name
            result=runner.test(step['solution'].replace(old,new),step)
            rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
            assert rejected,(name,result)
            records.append({'area':label,'mutation':name,'status':'rejected','runner_status':result['status']})
            print(name+': rejected',flush=True)
    report={'backend':'real PowerShell 7.6.8 / loopback HTTP','prediction_stdout':stdout,
            'references_passed':3,'mutants_rejected':len(records),'mutants_passed':0,'cases':records}
    (ROOT/'outputs/a-notu-ps23-http-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
