"""Capture real managed-lab S4U tickets, DC events and LDAP results (no secrets)."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox.ad_vm_process import execute,ensure_ready
from sandbox.ad_ldap_client import probe


def main():
    ensure_ready('PF-DC01')
    ensure_ready('PF-APP01')
    result=execute(". C:\\Pafta\\s4u_probe.ps1\n@('classic','rbcd','missing','blocked') | ForEach-Object {Invoke-PaftaS4U $_} | ConvertTo-Json -Depth 6",guest='PF-APP01',timeout=200)
    if result['code']:
        raise RuntimeError(result['stderr'])
    flows=json.loads(result['stdout'])
    if [r['ok'] for r in flows]!=[True,True,False,False]:
        raise RuntimeError('Unexpected live S4U result: '+str(flows))
    first=min(r['started'] for r in flows)
    last=max(r['finished'] for r in flows)
    event_code=("Get-WinEvent -FilterHashtable @{LogName='Security';Id=4769;StartTime=([DateTime]'"+first+"').AddSeconds(-2);EndTime=([DateTime]'"+last+"').AddSeconds(2)} | ForEach-Object {$_.ToXml()}")
    events=execute(event_code,timeout=60)
    ldap={mode:probe(mode) for mode in ('valid','none','wrong','signed','unsigned','bad-ca','bad-name','starttls')}
    output=ROOT/'outputs/ad-live-evidence.json'
    output.write_text(json.dumps({'s4u':flows,'ldap':ldap,'events4769_xml':events['stdout']},ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print('Real S4U modes:',[(r['mode'],r['ok']) for r in flows])
    print('Real LDAP modes:',{k:v['ok'] for k,v in ldap.items()})
    print('Evidence:',output)


if __name__=='__main__':
    main()
