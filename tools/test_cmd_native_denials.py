"""CM22/CM24 real Registry and NTFS Deny regressions, no command mock."""
import json
import os
from pathlib import Path
import sys
import winreg

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get
from sandbox.cmd_deny_fixtures import registry_fixture,file_fixture


def rollback_faults():
    class ProbeFault(Exception):pass
    for create in (registry_fixture,file_fixture):
        try:
            with create() as lab:
                lab.deny_read()
                if create is registry_fixture:
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,lab.relative_path):pass
                    except PermissionError as error:assert error.winerror==5
                    else:raise AssertionError('Registry was not denied')
                else:
                    try:lab.path.read_bytes()
                    except PermissionError:pass
                    else:raise AssertionError('File was not denied')
                raise ProbeFault()
        except ProbeFault:pass
        if create is registry_fixture:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,lab.relative_path):pass
            except FileNotFoundError:pass
            else:raise AssertionError('Registry cleanup leaked')
        else:assert not lab.path.exists()
    print('real Deny plus fault-path restoration/deletion: passed',flush=True)


def main():
    rollback_faults()
    specifications=[
        ('cm22','reg.exe query "%kok%" >nul',[
            ('omit key readability probe','reg.exe query "%kok%" >nul 2>nul || goto hata','rem readability probe omitted'),
            ('ignore key failure','reg.exe query "%kok%" >nul 2>nul || goto hata','reg.exe query "%kok%" >nul 2>nul'),
            ('failure exit zero','exit /b 1','exit /b 0'),
            ('append search report','>"arama.txt"','>>"arama.txt"'),
        ]),
        ('cm24','whoami.exe /priv',[
            ('ignore real type denial','(type "%dosya%" >"okuma.txt") 2>nul || goto hata','(type "%dosya%" >"okuma.txt") 2>nul'),
            ('append stale read report','>"okuma.txt"','>>"okuma.txt"'),
            ('failure exit zero','exit /b 1','exit /b 0'),
            ('read wrong source','type "%dosya%"','type "delil dosyasi.txt"'),
        ]),
    ]
    records=[]
    for lesson,marker,mutations in specifications:
        step=next(s for s in Library().lesson('cmd',lesson)['steps'] if s['kind']=='gorev' and marker in s.get('solution',''))
        runner=for_step(get('cmd'),step)
        result=runner.test(step['solution'],step)
        assert result['status']=='pass',(lesson,'reference',result)
        print(lesson+': native reference passed',flush=True)
        for name,old,new in mutations:
            assert old in step['solution'],name
            result=runner.test(step['solution'].replace(old,new),step)
            rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
            assert rejected,(lesson,name,result)
            records.append({'lesson':lesson,'mutation':name,'status':'rejected','runner_status':result['status']})
            print(lesson+' '+name+': rejected',flush=True)
    report={'backend':'real Windows cmd.exe / reg.exe / type / icacls / native DACL APIs',
            'references_passed':2,'mutants_rejected':len(records),'mutants_passed':0,'cases':records,
            'fault_cleanup':'Owned Registry and file Deny verified, original DACL restored and owned objects deleted after injected Python exception.',
            'scope':'New GUID HKCU key and new temporary file only; no system ACL or service change.'}
    (ROOT/'outputs/a-notu-cmd-native-denials-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
