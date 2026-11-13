"""PS24 offline files: Windows-produced EVTX and native JEA data files.

Event payloads are synthetic classic EVT records converted by Windows, not
AppLocker enforcement evidence. No live policy/channel/endpoint is changed.
"""
import os
from pathlib import Path
import runpy
import subprocess

SOURCE='Microsoft-Windows-AppLocker'
BOOTSTRAP=r'''
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$null=New-Item -ItemType Directory -Path RoleCapabilities -Force
New-PSRoleCapabilityFile -Path RoleCapabilities\Reader.psrc -VisibleCmdlets 'Get-Service',@{Name='Restart-Service';Parameters=@{Name='Name';ValidateSet=@('Dns','Spooler')}} -VisibleExternalCommands 'C:\Windows\System32\whoami.exe'
New-PSRoleCapabilityFile -Path RoleCapabilities\Inventory.psrc -VisibleCmdlets 'Get-Process' -VisibleProviders 'FileSystem'
New-PSSessionConfigurationFile -Path limited.pssc -SessionType RestrictedRemoteServer -RunAsVirtualAccount -RoleDefinitions @{'PAFTA\Analistler'=@{RoleCapabilities=@('Reader','Inventory')};'PAFTA\SaltOku'=@{RoleCapabilities=@('Inventory')}}
New-PSSessionConfigurationFile -Path alternate.pssc -SessionType Default -RoleDefinitions @{'PAFTA\Analistler'=@{RoleCapabilities=@('Inventory')}}
if(-not (Test-PSSessionConfigurationFile -Path limited.pssc)) {throw 'Invalid native PSSC'}
'''


def build():
    fixture=runpy.run_path(str(Path(__file__).with_name('ps_evtx_fixtures.py')))
    evtx=fixture['evtx']
    info,warn,error=fixture['BILGI'],fixture['UYARI'],fixture['HATA']
    rows=[]
    for offset,eid in enumerate(range(8002,8008)):
        severity={0:info,1:warn,2:error}[offset%3]
        rows.append((eid,severity,offset,SOURCE,
                     ['EXE' if eid<8005 else 'SCRIPT',rf'C:\Pafta\file {eid}.exe',
                      f'Rule-{eid}','S-1-5-21-1000-2000-3000-1105']))
    rows.extend([
        (8001,info,10,SOURCE,['ignored']),
        (8008,warn,11,SOURCE,['ignored']),
        (8004,error,12,'Other-Provider',['EXE','fake.exe','fake','fake']),
    ])
    evtx('applocker.evtx',rows)
    evtx('alternate.evtx',[(8004,error,0,SOURCE,['EXE',r'C:\Different\changed.dll','Changed Rule','S-1-5-18'])])
    evtx('missing-fields.evtx',[(8004,error,0,SOURCE,['EXE','only-path'])])
    evtx('empty.evtx',[])
    Path('corrupt.evtx').write_bytes(b'not an EVTX file')
    script=Path('build-jea.ps1')
    script.write_text(BOOTSTRAP,encoding='utf-8-sig',newline='\n')
    env=dict(os.environ)
    env['PSModulePath']=str(Path(env.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/Modules')
    exe=Path(env.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(exe),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script.resolve())],
                          capture_output=True,env=env,timeout=25,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError('Native JEA fixture creation failed: '+result.stderr.decode('utf-8','replace')[:500])
    # Windows PowerShell 5.1 emits UTF-16; preserve the native-generated data
    # while keeping the teaching files UTF-8/LF. BOM tells 5.1 the encoding.
    for path in [*Path('.').glob('*.pssc'),*Path('RoleCapabilities').glob('*.psrc')]:
        raw=path.read_bytes()
        text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        path.write_text(text.replace('\r\n','\n'),encoding='utf-8-sig',newline='\n')
    Path('dynamic.pssc').write_text("@{ SessionType = $(Set-Content -LiteralPath executed.txt -Value BAD) }\n",encoding='utf-8')


if __name__=='__tezgah__':
    build()
