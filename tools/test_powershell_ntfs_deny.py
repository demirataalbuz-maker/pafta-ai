"""PS22: actual NTFS deny, independent read witness and rollback faults."""
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
    step=next(s for s in Library().lesson('powershell','ps22')['steps']
              if s['kind']=='gorev' and 'function Read-State' in s.get('solution',''))
    runner=for_step(get('powershell'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    print('native NTFS reference and rollback fault: passed',flush=True)
    mutations=[
        ('allow instead of deny',"($sid,$Girdi[1],'Deny')","($sid,$Girdi[1],'Allow')"),
        ('always deny read',"($sid,$Girdi[1],'Deny')","($sid,'ReadData','Deny')"),
        ('do not apply ACL','Set-Acl -LiteralPath $path -AclObject $changed',"Write-Verbose 'apply omitted'"),
        ('omit rollback','Set-Acl -LiteralPath $path -AclObject $original',"Write-Verbose 'rollback omitted'"),
        ('restore modified ACL','Set-Acl -LiteralPath $path -AclObject $original','Set-Acl -LiteralPath $path -AclObject $changed'),
        ('swallow permission denial',"{ 'DENIED' } else { throw }","{ 'OK:0' } else { throw }"),
        ('zero byte incorrectly denied',"'OK:'+([IO.File]::ReadAllBytes($File).Length)","if ([IO.File]::ReadAllBytes($File).Length -eq 0) { 'DENIED' } else { 'OK:'+([IO.File]::ReadAllBytes($File).Length) }"),
        ('fake restored report','-eq $original.Sddl','-ne $original.Sddl'),
    ]
    records=[]
    for name,old,new in mutations:
        assert old in step['solution'],name
        result=runner.test(step['solution'].replace(old,new),step)
        rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
        assert rejected,(name,result)
        records.append({'mutation':name,'status':'rejected','runner_status':result['status']})
        print(name+': rejected',flush=True)
    report={'backend':'real Windows PowerShell 5.1 / NTFS / current token',
            'references_passed':1,'mutants_rejected':len(records),'mutants_passed':0,'cases':records,
            'witness':'Actual Set-Acl plus independent File.ReadAllBytes; fault after applying Deny; original SDDL and bytes restored.'}
    (ROOT/'outputs/a-notu-ps22-ntfs-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
