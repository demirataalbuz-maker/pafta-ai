"""Transport real PowerShell jobs to Pafta's managed VMware lab.

The guest owns the learner timeout and a Windows kill-on-close Job Object.
VMware Tools transport requires no exposed WinRM listener or shared host folder.
Passwords remain in the user's private local lab config; errors redact them.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

LAB = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Pafta/labs/ad'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def config():
    path = LAB / 'config.json'
    if not path.exists():
        raise RuntimeError('Pafta AD laboratuvarı kurulmamış. tools/setup_ad_vm.py ile bir kez kurun.')
    data = json.loads(path.read_text(encoding='utf8'))
    for name, guest in data['guests'].items():
        if name not in ('PF-DC01', 'PF-APP01'):
            raise ValueError('Bilinmeyen Pafta AD konuk adı.')
        vmx = Path(guest['vmx']).resolve()
        if not vmx.is_relative_to(LAB.resolve()) or vmx.suffix != '.vmx':
            raise ValueError('AD VM yolu yönetilen laboratuvar dışında.')
    return data


def call(data, guest_name, command, *args, auth=True, timeout=90):
    guest = data['guests'][guest_name]
    argv = [data['vmrun'], '-T', 'ws']
    if auth:
        argv += ['-gu', guest['username'], '-gp', guest['password']]
    argv += [command, guest['vmx'], *map(str, args)]
    try:
        p = subprocess.run(argv, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        # Never expose subprocess's argv (contains the local lab password).
        raise RuntimeError('VMware işlemi zaman aşımına uğradı: ' + command) from None
    if p.returncode:
        message = (p.stdout + p.stderr).decode('utf8', 'replace')
        message = message.replace(guest['password'], '[gizli]')
        raise RuntimeError('VMware ' + command + ': ' + message.strip()[:600])
    return p.stdout.decode('utf8', 'replace').strip()


def ensure_ready(guest='PF-DC01', timeout=180):
    data = config()
    if guest not in data['guests']:
        raise ValueError('Bilinmeyen AD konuk adı.')
    # Idempotent vmrun start starts only this managed guest, without a window.
    running = subprocess.run([data['vmrun'], '-T', 'ws', 'list'], capture_output=True, timeout=15, creationflags=NO_WINDOW)
    vmx = data['guests'][guest]['vmx']
    if vmx.casefold() not in running.stdout.decode('utf8', 'replace').casefold():
        call(data, guest, 'start', 'nogui', auth=False, timeout=60)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            if call(data, guest, 'checkToolsState', auth=False, timeout=15) in ('installed', 'running'):
                # Headless Workstation can report 'installed' for a live Tools
                # service. Confirm a real authenticated operation, not the label.
                marker = call(data, guest, 'fileExistsInGuest', r'C:\Pafta\bootstrap-ready.txt', timeout=15)
                if 'file exists' in marker.lower() and 'not exist' not in marker.lower():
                    return data
        except RuntimeError:
            pass
        time.sleep(2)
    raise RuntimeError('AD VM başlatıldı fakat VMware Tools hazır olmadı. Kurulum durumunu kontrol edin.')


GUARD = r'''param([string]$Folder)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PaftaGuestJob {
 [StructLayout(LayoutKind.Sequential)] struct Basic {
  public long ProcessTime,JobTime; public uint Flags;
  public UIntPtr MinWorking,MaxWorking; public uint ActiveLimit;
  public UIntPtr Affinity; public uint Priority,Scheduling;
 }
 [StructLayout(LayoutKind.Sequential)] struct Io {public ulong A,B,C,D,E,F;}
 [StructLayout(LayoutKind.Sequential)] struct Extended {public Basic Basic;public Io Io;public UIntPtr A,B,C,D;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a,string b);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr h,int c,ref Extended p,uint n);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr h,IntPtr p);
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 static IntPtr handle;
 public static void AttachSelf() {
  handle=CreateJobObject(IntPtr.Zero,null);
  Extended e=new Extended();e.Basic.Flags=0x2000;
  if(handle==IntPtr.Zero || !SetInformationJobObject(handle,9,ref e,(uint)Marshal.SizeOf(e)) || !AssignProcessToJobObject(handle,GetCurrentProcess()))
   throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
 }
}
'@
[PaftaGuestJob]::AttachSelf()
$request = Get-Content -Raw -LiteralPath "$Folder\request.json" | ConvertFrom-Json
$output = "$Folder\stdout.txt"
$errorFile = "$Folder\stderr.txt"
function Read-LiveFile([string]$Path) {
 if(-not (Test-Path $Path)){return ''}
 $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 $reader=New-Object IO.StreamReader($stream,[Text.Encoding]::UTF8)
 try { $reader.ReadToEnd() } finally { $reader.Dispose() }
}
try {
 $p=Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',"$Folder\learner.ps1") -WindowStyle Hidden -WorkingDirectory $Folder -RedirectStandardInput "$Folder\stdin.txt" -RedirectStandardOutput $output -RedirectStandardError $errorFile -PassThru
 $null=$p.Handle
 $done=$p.WaitForExit([int]$request.timeout * 1000)
 if($done){$p.WaitForExit();$code=$p.ExitCode}else{$code=124}
 $out=Read-LiveFile $output
 $err=Read-LiveFile $errorFile
 $result=@{code=$code;stdout=$out;stderr=$err;timeout=(-not $done)}
} catch { $result=@{code=70;stdout='';stderr=$_.Exception.Message;timeout=$false} }
$json=$result|ConvertTo-Json -Compress
[IO.File]::WriteAllText("$Folder\result.json",$json,(New-Object Text.UTF8Encoding $false))
# Process exit closes the job handle and terminates ALL descendants, on normal
# return as well as timeout; the host doesn't merely kill vmrun.exe.
[Environment]::Exit(0)
'''


def execute(code, stdin='', guest='PF-DC01', timeout=30):
    if not 1 <= timeout <= 600:
        raise ValueError('AD betik süresi 1–600 saniye olmalı.')
    data = ensure_ready(guest)
    job = 'job_' + uuid.uuid4().hex
    target = 'C:\\Pafta\\' + job
    with tempfile.TemporaryDirectory(prefix='pafta_advm_') as folder:
        folder = Path(folder)
        files = {
            'guard.ps1': GUARD,
            'learner.ps1': '[Console]::InputEncoding = New-Object Text.UTF8Encoding $false\n[Console]::OutputEncoding = New-Object Text.UTF8Encoding $false\n$OutputEncoding = [Console]::OutputEncoding\n$ErrorActionPreference = "Stop"\n' + code,
            'request.json': json.dumps({'timeout': timeout}), 'stdin.txt': stdin,
        }
        call(data, guest, 'createDirectoryInGuest', target)
        try:
            for name, content in files.items():
                path = folder/name
                path.write_text(content, encoding='utf-8-sig' if name.endswith('.ps1') else 'utf8', newline='\n')
                call(data, guest, 'copyFileFromHostToGuest', path, target+'\\'+name)
            call(data, guest, 'runProgramInGuest', r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', target+'\\guard.ps1', '-Folder', target, timeout=timeout+40)
            result = folder/'result.json'
            call(data, guest, 'copyFileFromGuestToHost', target+'\\result.json', result)
            return json.loads(result.read_text(encoding='utf-8-sig'))
        finally:
            try:
                call(data, guest, 'deleteDirectoryInGuest', target, timeout=15)
            except RuntimeError:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--guest', choices=('PF-DC01', 'PF-APP01'), default='PF-DC01')
    parser.add_argument('file')
    args = parser.parse_args()
    try:
        result = execute(Path(args.file).read_text(encoding='utf-8-sig'), sys.stdin.read(), args.guest, timeout=60)
        sys.stdout.buffer.write(result['stdout'].encode('utf8'))
        sys.stderr.buffer.write(result['stderr'].encode('utf8'))
        if result['timeout']:
            sys.stderr.buffer.write(b'\nPafta AD: guest timeout; descendant processes closed.\n')
        return result['code']
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 70


if __name__ == '__main__':
    sys.exit(main())
