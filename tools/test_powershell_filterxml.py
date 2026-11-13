"""PS27 real FilterXml / EventLogRecord.ToXml regression acceptance."""
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
    step=next(s for s in Library().lesson('powershell','ps27')['steps']
              if s['kind']=='gorev' and '-FilterXml' in s.get('solution',''))
    runner=for_step(get('powershell'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    print('real FilterXml/ToXml reference: passed',flush=True)
    mutations=[
        ('exclusive level','Level&lt;=$level','Level&lt;$level'),
        ('OR instead of AND','and (Level','or (Level'),
        ('reverse record order',' -Oldest',''),
        ('exclusive ID zero','$id -lt 0','$id -le 0'),
        ('exclusive ID maximum','$id -gt 65535','$id -ge 65535'),
        ('exclusive level zero','$level -lt 0','$level -le 0'),
        ('exclusive level maximum','$level -gt 5','$level -ge 5'),
        ('missing namespace','http://schemas.microsoft.com/win/2004/08/events/event','http://invalid.test/event'),
        ('discard Data fields','data=$data','data=@()'),
        ('hide corrupt EVTX',"if ($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*') { throw }",'if ($false) { throw }'),
        ('leak working copy','Remove-Item -LiteralPath $staged -ErrorAction Stop',"Write-Verbose 'cleanup omitted'"),
    ]
    records=[]
    for name,old,new in mutations:
        assert old in step['solution'],name
        result=runner.test(step['solution'].replace(old,new),step)
        rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
        assert rejected,(name,result)
        records.append({'mutation':name,'status':'rejected','runner_status':result['status']})
        print(name+': rejected',flush=True)
    report={'backend':'real Windows PowerShell 5.1 / wevtutil EVTX / Get-WinEvent',
            'references_passed':1,'mutants_rejected':len(records),'mutants_passed':0,'cases':records,
            'reader_limit':'file:// required; ampersand source names are queried through a disposable GUID-named copy; working-directory path must not contain &.'}
    (ROOT/'outputs/a-notu-ps27-filterxml-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
