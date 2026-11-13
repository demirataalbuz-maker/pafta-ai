"""Prepare NEW Pafta VMware guests, never overwrite an existing virtual disk.

Media: official Windows Server 2025 Evaluation + installed VMware Tools ISO.
Private state lives under LOCALAPPDATA/Pafta/labs/ad, outside the repository.
This command does not alter the host's domain, DNS, firewall, or existing VMs.
"""
import argparse
import base64
import json
import ipaddress
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
LAB = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Pafta/labs/ad'
VMWARE = Path(r'C:\Program Files (x86)\VMware\VMware Workstation')
sys.path.insert(0, str(ROOT))


def password():
    return 'Pf9!' + secrets.token_urlsafe(24)


def answer_file(name, secret):
    boot = "$p=Get-PSDrive -PSProvider FileSystem|Where-Object {Test-Path ($_.Root+'bootstrap.ps1')}|Select-Object -First 1; & ($p.Root+'bootstrap.ps1')"
    encoded = base64.b64encode(boot.encode('utf-16-le')).decode()
    component = 'processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"'
    return f'''<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
 <settings pass="windowsPE">
  <component name="Microsoft-Windows-International-Core-WinPE" {component}>
   <SetupUILanguage><UILanguage>en-US</UILanguage></SetupUILanguage>
   <InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale>
  </component>
  <component name="Microsoft-Windows-Setup" {component}>
   <DiskConfiguration><Disk wcm:action="add"><DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
    <CreatePartitions><CreatePartition wcm:action="add"><Order>1</Order><Type>Primary</Type><Size>500</Size></CreatePartition><CreatePartition wcm:action="add"><Order>2</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition></CreatePartitions>
    <ModifyPartitions><ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Active>true</Active><Format>NTFS</Format><Label>System</Label></ModifyPartition><ModifyPartition wcm:action="add"><Order>2</Order><PartitionID>2</PartitionID><Format>NTFS</Format><Label>Windows</Label><Letter>C</Letter></ModifyPartition></ModifyPartitions>
   </Disk><WillShowUI>OnError</WillShowUI></DiskConfiguration>
   <ImageInstall><OSImage><InstallFrom><MetaData wcm:action="add"><Key>/IMAGE/INDEX</Key><Value>1</Value></MetaData></InstallFrom><InstallTo><DiskID>0</DiskID><PartitionID>2</PartitionID></InstallTo><WillShowUI>OnError</WillShowUI></OSImage></ImageInstall>
   <UserData><AcceptEula>true</AcceptEula><FullName>Pafta Lab</FullName><Organization>Pafta</Organization></UserData>
  </component>
 </settings>
 <settings pass="specialize"><component name="Microsoft-Windows-Shell-Setup" {component}><ComputerName>{escape(name)}</ComputerName><TimeZone>UTC</TimeZone></component></settings>
 <settings pass="oobeSystem">
  <component name="Microsoft-Windows-International-Core" {component}><InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale></component>
  <component name="Microsoft-Windows-Shell-Setup" {component}>
   <OOBE><HideEULAPage>true</HideEULAPage><HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideLocalAccountScreen>true</HideLocalAccountScreen><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE><ProtectYourPC>3</ProtectYourPC></OOBE>
   <UserAccounts><AdministratorPassword><Value>{escape(secret)}</Value><PlainText>true</PlainText></AdministratorPassword></UserAccounts>
   <AutoLogon><Password><Value>{escape(secret)}</Value><PlainText>true</PlainText></Password><Enabled>true</Enabled><LogonCount>2</LogonCount><Username>Administrator</Username></AutoLogon>
   <FirstLogonCommands><SynchronousCommand wcm:action="add"><Order>1</Order><Description>Pafta VMware Tools bootstrap</Description><CommandLine>powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}</CommandLine></SynchronousCommand></FirstLogonCommands>
  </component>
 </settings>
</unattend>
'''


BOOTSTRAP = r'''$ErrorActionPreference = 'Stop'
New-Item C:\Pafta -ItemType Directory -Force | Out-Null
Start-Transcript C:\Pafta\bootstrap.log -Append
$tools = Get-PSDrive -PSProvider FileSystem | Where-Object {Test-Path ($_.Root + 'setup64.exe')} | Select-Object -First 1
if (-not $tools) { throw 'VMware Tools ISO not found' }
$p = Start-Process ($tools.Root+'setup64.exe') -ArgumentList '/s /v"/qn REBOOT=R"' -Wait -PassThru
if ($p.ExitCode -notin @(0,3010)) { throw "VMware Tools failed: $($p.ExitCode)" }
'ready' | Set-Content C:\Pafta\bootstrap-ready.txt
Stop-Transcript
Restart-Computer -Force
'''


def prepare(name, secret, iso):
    folder = LAB / name
    vmx = folder / (name + '.vmx')
    if vmx.exists():
        return vmx
    folder.mkdir(parents=True, exist_ok=True)
    disk = folder / 'disk.vmdk'
    if disk.exists():
        raise RuntimeError('Existing disk without VM config; inspect manually: ' + str(disk))
    seed = folder / 'seed'
    seed.mkdir(exist_ok=True)
    (seed / 'Autounattend.xml').write_text(answer_file(name, secret), encoding='utf8', newline='\n')
    (seed / 'bootstrap.ps1').write_text(BOOTSTRAP, encoding='utf-8-sig', newline='\n')
    seed_iso = folder / 'seed.iso'
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'tools/ad_seed_iso.ps1'), '-Folder', str(seed), '-Output', str(seed_iso)], check=True)
    subprocess.run([str(VMWARE/'vmware-vdiskmanager.exe'), '-c', '-s', '60GB', '-a', 'lsilogic', '-t', '0', str(disk)], check=True, capture_output=True)
    settings = {
        '.encoding': 'UTF-8', 'config.version': '8', 'virtualHW.version': '19',
        'displayName': 'Pafta ' + name, 'guestOS': 'windows2019srv-64',
        'memsize': '3072', 'numvcpus': '2', 'firmware': 'bios',
        'scsi0.present': 'TRUE', 'scsi0.virtualDev': 'lsisas1068',
        'scsi0:0.present': 'TRUE', 'scsi0:0.fileName': 'disk.vmdk',
        'sata0.present': 'TRUE', 'ethernet0.present': 'TRUE',
        'pciBridge0.present': 'TRUE',
        'ethernet0.connectionType': 'hostonly', 'ethernet0.virtualDev': 'e1000e',
        'ethernet0.addressType': 'generated', 'usb.present': 'TRUE',
        'floppy0.present': 'FALSE', 'sound.present': 'FALSE',
        'bios.bootOrder': 'cdrom,hdd', 'bios.bootDelay': '1000',
        'isolation.tools.copy.disable': 'TRUE', 'isolation.tools.paste.disable': 'TRUE',
        'sharedFolder.maxNum': '0', 'tools.syncTime': 'TRUE',
    }
    for bridge in (4,5,6,7):
        settings.update({f'pciBridge{bridge}.present': 'TRUE', f'pciBridge{bridge}.virtualDev': 'pcieRootPort', f'pciBridge{bridge}.functions': '8'})
    for index, path in enumerate((iso, seed_iso, VMWARE/'windows.iso')):
        settings.update({f'sata0:{index}.present': 'TRUE', f'sata0:{index}.deviceType': 'cdrom-image', f'sata0:{index}.fileName': str(path), f'sata0:{index}.startConnected': 'TRUE'})
    vmx.write_text(''.join(f'{k} = "{v}"\n' for k,v in settings.items()), encoding='utf8', newline='\n')
    return vmx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--provision', action='store_true', help='Wait for Tools, then configure the isolated AD forest, CA and member.')
    args = parser.parse_args()
    iso = LAB/'media/WindowsServer2025-eval-en-us.iso'
    if not iso.exists():
        raise SystemExit('Download the approved Microsoft ISO first: ' + str(iso))
    LAB.mkdir(parents=True, exist_ok=True)
    subprocess.run(['icacls.exe', str(LAB), '/inheritance:r', '/grant:r', os.environ['USERDOMAIN']+'\\'+os.environ['USERNAME']+':(OI)(CI)F'], check=True, capture_output=True)
    config_path = LAB/'config.json'
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf8'))
    else:
        if any((LAB/name/(name+'.vmx')).exists() for name in ('PF-DC01','PF-APP01')):
            raise RuntimeError('Existing Pafta VM without its private config; restore the original config before continuing.')
        config = {'vmrun': str(VMWARE/'vmrun.exe'), 'domain': 'pafta.test', 'guests': {name: {'username': 'Administrator', 'password': password()} for name in ('PF-DC01','PF-APP01')}}
        config_path.write_text(json.dumps(config, indent=2), encoding='utf8')
        # Host user's private local profile; credentials never enter Git/output.
        subprocess.run(['icacls.exe', str(config_path), '/inheritance:r', '/grant:r', os.environ['USERDOMAIN']+'\\'+os.environ['USERNAME']+':F'], check=True, capture_output=True)
    for name, guest in config['guests'].items():
        guest['vmx'] = str(prepare(name, guest['password'], iso))
        config_path.write_text(json.dumps(config, indent=2), encoding='utf8')
        if args.start or args.provision:
            subprocess.run([config['vmrun'], '-T', 'ws', 'start', guest['vmx'], 'nogui'], check=True, timeout=120, capture_output=True)
        print(name, 'prepared' + (' and started' if args.start else ''))
    if args.provision:
        provision(config, config_path)


def provision(config, config_path):
    """Resume provisioning stages; no credentials or host changes in stdout."""
    from sandbox import ad_vm_process as vm
    import re
    dhcp = Path(r'C:\ProgramData\VMware\vmnetdhcp.conf').read_text()
    section = dhcp.split('Virtual ethernet segment 1', 1)[1].split('# End', 1)[0]
    match = re.search(r'subnet\s+(\S+)\s+netmask\s+(\S+)', section)
    network = ipaddress.ip_network(match[1]+'/'+match[2])
    if network.prefixlen != 24:
        raise RuntimeError('This lab currently requires a /24 VMware host-only subnet.')
    dc_ip, app_ip = str(network.network_address+10), str(network.network_address+11)
    config.update(dc_address=dc_ip, app_address=app_ip)
    def save():
        config_path.write_text(json.dumps(config, indent=2), encoding='utf8')
    save()
    def ready(name):
        end = time.monotonic()+1200
        while time.monotonic() < end:
            try:
                if vm.call(config, name, 'checkToolsState', auth=False, timeout=10) in ('installed', 'running'):
                    marker = vm.call(config, name, 'fileExistsInGuest', r'C:\Pafta\bootstrap-ready.txt', timeout=10)
                    if 'file exists' in marker.lower() and 'not exist' not in marker.lower():
                        print(name, 'Tools ready', flush=True)
                        return
            except RuntimeError:
                pass
            time.sleep(10)
        raise RuntimeError(name+' Windows/Tools installation did not finish in 20 minutes.')
    def ps_quote(value):
        return "'"+value.replace("'", "''")+"'"
    def script(name, file, args):
        source = (ROOT/'sandbox/ad_vm'/file).read_text(encoding='utf8')
        code = '& {\n'+source+'\n} ' + ' '.join('-'+key+' '+ps_quote(value) for key,value in args.items())
        result = vm.execute(code, guest=name, timeout=600)
        if result['code'] != 0:
            # PowerShell could echo source parameters; redact both guest secrets.
            error = result['stderr']
            for guest in config['guests'].values():
                error = error.replace(guest['password'], '[gizli]')
            raise RuntimeError(error[:1000])
        print(result['stdout'].strip(), flush=True)
    def reboot(name, old_guest=None):
        before=dict(config)
        before['guests']=dict(config['guests'])
        if old_guest is not None:before['guests'][name]=old_guest
        vm.call(before, name, 'runProgramInGuest', '-noWait', r'C:\Windows\System32\shutdown.exe', '/r', '/t', '2', '/f', timeout=20)
        time.sleep(40)
        ready(name)
    ready('PF-DC01')
    # Windows VM firmware initially interprets a host local-time RTC. Explicitly
    # synchronize ONLY the disposable guests before issuing lab certificates.
    def sync_clock(name):
        now=datetime.now(timezone.utc).isoformat()
        code=("& 'C:\\Program Files\\VMware\\VMware Tools\\VMwareToolboxCmd.exe' timesync disable | Out-Null\n"
              "New-ItemProperty HKLM:\\SYSTEM\\CurrentControlSet\\Control\\TimeZoneInformation -Name RealTimeIsUniversal -Value 1 -PropertyType DWord -Force|Out-Null\n"
              "Set-Date -Date ([DateTime]::Parse('"+now+"').ToUniversalTime())|Out-Null")
        result=vm.execute(code,guest=name,timeout=30)
        if result['code']!=0:raise RuntimeError('Guest clock synchronization failed: '+name)
    sync_clock('PF-DC01')
    if not config.get('forest_installed'):
        script('PF-DC01', 'provision_dc.ps1', {'Stage':'forest','LabPassword':config['guests']['PF-DC01']['password'],'Address':dc_ip})
        config['forest_installed'] = True
        config['guests']['PF-DC01']['username'] = 'PAFTA\\Administrator'
        save()
        reboot('PF-DC01')
    if not config.get('directory_ready'):
        script('PF-DC01', 'provision_dc.ps1', {'Stage':'directory','LabPassword':config['guests']['PF-DC01']['password'],'Address':dc_ip})
        config['directory_ready'] = True
        save()
    if not config.get('ldaps_ready'):
        script('PF-DC01', 'provision_ldaps.ps1', {'Address':dc_ip})
        vm.call(config, 'PF-DC01', 'copyFileFromGuestToHost', r'C:\Pafta\root-ca.cer', str(LAB/'root-ca.cer'))
        config['ldaps_ready'] = True
        save()
        reboot('PF-DC01')
    if not config.get('templates_ready'):
        script('PF-DC01', 'provision_templates.ps1', {})
        config['templates_ready'] = True
        save()
    ready('PF-APP01')
    sync_clock('PF-APP01')
    if not config.get('member_joined'):
        script('PF-APP01', 'provision_app.ps1', {'LabPassword':config['guests']['PF-DC01']['password'],'Address':app_ip,'DcAddress':dc_ip})
        old_guest=dict(config['guests']['PF-APP01'])
        config['member_joined'] = True
        config['guests']['PF-APP01']['username'] = 'PAFTA\\Administrator'
        config['guests']['PF-APP01']['password'] = config['guests']['PF-DC01']['password']
        save()
        reboot('PF-APP01',old_guest)
    vm.call(config, 'PF-DC01', 'copyFileFromHostToGuest', str(ROOT/'sandbox/ad_vm/acl_probe.ps1'), r'C:\Pafta\acl_probe.ps1')
    vm.call(config, 'PF-DC01', 'copyFileFromHostToGuest', str(ROOT/'sandbox/ad_vm/enrollment_probe.ps1'), r'C:\Pafta\enrollment_probe.ps1')
    vm.call(config, 'PF-APP01', 'copyFileFromHostToGuest', str(ROOT/'sandbox/ad_vm/s4u_probe.ps1'), r'C:\Pafta\s4u_probe.ps1')
    print('Pafta AD forest, CA and member provisioning complete.', flush=True)


if __name__ == '__main__':
    main()
