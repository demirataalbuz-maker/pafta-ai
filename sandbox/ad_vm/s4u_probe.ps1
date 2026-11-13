# Real S4U to the member's own HOST service, then a real SMB read on the DC.
# Only the two managed lab machines and the fixed disposable lab user are used.
function Invoke-PaftaS4U {
    param([ValidateSet('classic','rbcd','missing','blocked')][string]$Mode)
    $ErrorActionPreference = 'Stop'
    if ($env:COMPUTERNAME -ne 'PF-APP01') { throw 'PF-APP01 lab guest required.' }
    Import-Module ActiveDirectory
    $server='PF-DC01.pafta.test'
    $front=Get-ADComputer PF-APP01 -Server $server
    $spn='cifs/PF-DC01.pafta.test'
    Set-ADComputer PF-APP01 -Server $server -Clear 'msDS-AllowedToDelegateTo'
    Set-ADAccountControl $front.DistinguishedName -Server $server -TrustedToAuthForDelegation:$false
    Set-ADComputer PF-DC01 -Server $server -PrincipalsAllowedToDelegateToAccount $null
    Set-ADAccountControl pf_s4u_user -Server $server -AccountNotDelegated:($Mode -eq 'blocked')
    if ($Mode -in @('classic','blocked')) {
        Set-ADComputer PF-APP01 -Server $server -Replace @{'msDS-AllowedToDelegateTo'=@($spn)}
        Set-ADAccountControl $front.DistinguishedName -Server $server -TrustedToAuthForDelegation:$true
    } elseif ($Mode -eq 'rbcd') {
        Set-ADComputer PF-DC01 -Server $server -PrincipalsAllowedToDelegateToAccount $front
    }
    $id=[guid]::NewGuid().ToString('N')
    $folder="C:\Pafta\s4u_$id"
    New-Item $folder -ItemType Directory | Out-Null
    $probe=@'
param([string]$Folder)
$ErrorActionPreference='Stop'
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public static class PaftaToken {
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(IntPtr t,int c,IntPtr p,int n,out int r);
 public static string Id(IntPtr token) {
  int n;GetTokenInformation(token,10,IntPtr.Zero,0,out n);
  IntPtr p=Marshal.AllocHGlobal(n);
  try {if(!GetTokenInformation(token,10,p,n,out n))throw new System.ComponentModel.Win32Exception();
   return ((uint)Marshal.ReadInt32(p,8)).ToString("x");
  } finally {Marshal.FreeHGlobal(p);}
 }
}
"@
$result=@{ok=$false;error='';tickets='';user='pf_s4u_user@pafta.test';started=[DateTime]::UtcNow.ToString('o')}
$identity=$null;$context=$null
try {
 # Isolate each managed experiment from cached machine/S4U service tickets.
 & klist.exe purge -li 0x3e7 2>&1 | Out-Null
 $identity=New-Object Security.Principal.WindowsIdentity('pf_s4u_user@pafta.test')
 $logon=[PaftaToken]::Id($identity.Token)
 $context=$identity.Impersonate()
 try {
  $text=[IO.File]::ReadAllText('\\PF-DC01.pafta.test\PaftaRead\proof.txt')
  $result.ok=($text -eq 'Pafta S4U proof')
 } finally { $context.Undo();$context=$null }
 $result.tickets=((& klist.exe -li $logon 2>&1)|Out-String)
} catch { $result.error=$_.Exception.Message }
finally {
 if($context){$context.Undo()}
 if($identity){
  $result.tickets=((& klist.exe -li $logon 2>&1)|Out-String)
  $identity.Dispose()
 }
}
$result.finished=[DateTime]::UtcNow.ToString('o')
$result|ConvertTo-Json -Depth 5|Set-Content "$Folder\proof.json" -Encoding UTF8
'@
    $path="$folder\probe.ps1"
    [IO.File]::WriteAllText($path,$probe,(New-Object Text.UTF8Encoding $true))
    $task="Pafta-S4U-$id"
    $action=New-ScheduledTaskAction -Execute powershell.exe -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $path -Folder $folder"
    try {
        Register-ScheduledTask -TaskName $task -Action $action -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 45)) -User SYSTEM -RunLevel Highest -Force | Out-Null
        Start-ScheduledTask -TaskName $task
        $end=[DateTime]::UtcNow.AddSeconds(40)
        while (-not (Test-Path "$folder\proof.json")) {
            if ([DateTime]::UtcNow -gt $end) { throw 'S4U proof task timeout.' }
            Start-Sleep -Milliseconds 200
        }
        $result=Get-Content -Raw "$folder\proof.json"|ConvertFrom-Json
        $result|Add-Member NoteProperty mode $Mode
        $result
    } finally {
        Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
        Set-ADAccountControl pf_s4u_user -Server $server -AccountNotDelegated:$false
        Set-ADComputer PF-APP01 -Server $server -Clear 'msDS-AllowedToDelegateTo'
        Set-ADAccountControl $front.DistinguishedName -Server $server -TrustedToAuthForDelegation:$false
        Set-ADComputer PF-DC01 -Server $server -PrincipalsAllowedToDelegateToAccount $null
        Remove-Item -LiteralPath $folder -Recurse -Force
    }
}
