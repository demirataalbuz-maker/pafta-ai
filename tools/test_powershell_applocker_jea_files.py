"""PS24 real EVTX/JEA data-file reading and semantic mutation acceptance."""
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
    steps=Library().lesson('powershell','ps24')['steps']
    specifications=[
        ('EVTX',lambda code:"Level<=$level" in code,[
            ('exclusive level','Level<=$level','Level<$level'),
            ('exclude ID 8002','EventID>=8002','EventID>8002'),
            ('exclude ID 8007','EventID<=8007','EventID<8007'),
            ('wrong provider',"Provider[@Name='Microsoft-Windows-AppLocker']","Provider[@Name='Other-Provider']"),
            ('reverse order',' -Oldest',''),
            ('audit mislabeled block',"8003 {'AUDIT'}","8003 {'BLOCK'}"),
            ('hide missing payload fields',"if ($event.Properties.Count -ne 4) { throw 'Beklenmeyen egitim kaydi semasi' }",'')
        ]),
        ('JEA',lambda code:'$configuration=Import-PowerShellDataFile' in code,[
            ('wrong selected group','$group=$Girdi[1]',"$group='PAFTA\\Analistler'"),
            ('drop provider list','providers=@($role.VisibleProviders | Where-Object { $null -ne $_ })','providers=@()'),
            ('hardcoded virtual account','virtual_account=[bool]$configuration.RunAsVirtualAccount','virtual_account=$true'),
            ('flatten command constraints','cmdlets=@($role.VisibleCmdlets | Where-Object { $null -ne $_ })','cmdlets=@($role.VisibleCmdlets | ForEach-Object { if ($_ -is [string]) { $_ } else { $_.Name } })'),
            ('execute configuration instead of data import','Import-PowerShellDataFile -LiteralPath $Girdi[0]','Invoke-Expression (Get-Content -LiteralPath $Girdi[0] -Raw)'),
            ('string false accepted',"if ($configuration.ContainsKey('RunAsVirtualAccount') -and $configuration.RunAsVirtualAccount -isnot [bool]) { throw 'Sanal hesap degeri boolean olmali' }",'')
        ]),
    ]
    records=[]
    for area,select,mutations in specifications:
        step=next(s for s in steps if s['kind']=='gorev' and select(s.get('solution','')))
        runner=for_step(get('powershell'),step)
        result=runner.test(step['solution'],step)
        assert result['status']=='pass',(area,'reference',result)
        print(area+': reference passed',flush=True)
        for name,old,new in mutations:
            assert old in step['solution'],name
            result=runner.test(step['solution'].replace(old,new),step)
            rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
            assert rejected,(name,result)
            records.append({'area':area,'mutation':name,'status':'rejected','runner_status':result['status']})
            print(name+': rejected',flush=True)
    report={'backend':'real Windows Get-WinEvent EVTX / native-generated JEA data files',
            'event_payload':'synthetic classic EVT converted to real EVTX; not actual AppLocker policy enforcement evidence',
            'references_passed':2,'mutants_rejected':len(records),'mutants_passed':0,'cases':records,
            'scope':'Offline file reading; no live policy/channel or registered JEA endpoint is changed.'}
    (ROOT/'outputs/a-notu-ps24-files-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
