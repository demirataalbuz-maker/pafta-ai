function Test-PaftaEnrollment {
 param([ValidateSet('PaftaClientLegacy','PaftaClientPending','PaftaClientSigned','PaftaServerOnly','PaftaClientDraft','PaftaClientEditable')][string]$Template)
 $ErrorActionPreference='Stop'
 if($env:COMPUTERNAME -ne 'PF-DC01'){throw 'Managed PF-DC01 guest required.'}
 if(-not ('PaftaEnrollToken' -as [type])){
  Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class PaftaEnrollToken {
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool LogonUser(string u,string d,string p,int t,int provider,out IntPtr token);
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr token);
 public static IntPtr Open(string password){IntPtr token;if(!LogonUser("pf_s4u_user","PAFTA",password,3,0,out token))throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());return token;}
}
'@
 }
 $folder='C:\Pafta\enroll_'+[guid]::NewGuid().ToString('N')
 New-Item $folder -ItemType Directory|Out-Null
 $inf=@'
[Version]
Signature="$Windows NT$"
[NewRequest]
Subject="CN=Pafta enrollment proof"
KeyLength=2048
MachineKeySet=TRUE
Exportable=FALSE
RequestType=PKCS10
'@
 $inf|Set-Content "$folder\request.inf" -Encoding ASCII
 $token=[IntPtr]::Zero;$context=$null
 try {
  & certreq.exe -new -q -f "$folder\request.inf" "$folder\request.req"|Out-Null
  if($LASTEXITCODE -ne 0){throw 'CSR generation failed'}
  $request=[IO.File]::ReadAllText("$folder\request.req")
  $secret=Get-Content -Raw C:\Pafta\lab-secret.json|ConvertFrom-Json
  $caName=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\CertSvc\Configuration').Active
  $token=[PaftaEnrollToken]::Open($secret.password)
  $identity=[Security.Principal.WindowsIdentity]::new($token)
  $context=$identity.Impersonate()
  try {
   for($attempt=0;$attempt -lt 15;$attempt++) {
    try {
     $ca=New-Object -ComObject CertificateAuthority.Request
     $disposition=$ca.Submit(0x100,$request,"CertificateTemplate:$Template","PF-DC01\$caName")
     break
    } catch {
     # ServiceController reports Running before the CA RPC endpoint is ready.
     # Retry only the explicit transport-startup error; never turn a CA denial
     # into success or retry arbitrary certificate/policy failures.
     if($_.Exception.ToString() -notmatch '800706ba' -or $attempt -eq 14){throw}
     Start-Sleep -Seconds 1
    }
   }
   [pscustomobject]@{template=$Template;disposition=$disposition;request_id=$ca.GetRequestId();message=$ca.GetDispositionMessage()}
  } finally {$context.Undo();$context=$null;$identity.Dispose()}
 } finally {
  if($context){$context.Undo()}
  if($token -ne [IntPtr]::Zero){[void][PaftaEnrollToken]::CloseHandle($token)}
  Remove-Item -LiteralPath $folder -Recurse -Force
 }
}
