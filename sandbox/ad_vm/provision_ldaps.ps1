param([Parameter(Mandatory=$true)][string]$Address)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'PF-DC01') { throw 'Managed PF-DC01 guest required.' }
Import-Module ADCSAdministration
if (-not (Get-CATemplate | Where-Object Name -eq WebServer)) {
    Add-CATemplate -Name WebServer | Out-Null
}
$inf=@"
[Version]
Signature="`$Windows NT`$"
[NewRequest]
Subject="CN=PF-DC01.pafta.test"
KeySpec=1
KeyLength=2048
Exportable=FALSE
MachineKeySet=TRUE
ProviderName="Microsoft RSA SChannel Cryptographic Provider"
ProviderType=12
RequestType=PKCS10
KeyUsage=0xa0
[Extensions]
2.5.29.17="{text}"
_continue_="dns=PF-DC01.pafta.test&"
_continue_="ipaddress=$Address"
[EnhancedKeyUsageExtension]
OID=1.3.6.1.5.5.7.3.1
"@
$inf | Set-Content C:\Pafta\ldaps.inf -Encoding ASCII
& certreq.exe -new -machine -f C:\Pafta\ldaps.inf C:\Pafta\ldaps.req | Out-Null
if($LASTEXITCODE -ne 0){throw 'certreq -new failed'}
$caName=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\CertSvc\Configuration').Active
& certreq.exe -submit -q -f -config "PF-DC01\$caName" -attrib 'CertificateTemplate:WebServer' C:\Pafta\ldaps.req C:\Pafta\ldaps.cer | Out-Null
if($LASTEXITCODE -ne 0){throw 'certreq -submit failed'}
& certreq.exe -accept -machine C:\Pafta\ldaps.cer | Out-Null
if($LASTEXITCODE -ne 0){throw 'certreq -accept failed'}
$ca=Get-ChildItem Cert:\LocalMachine\My | Where-Object {$_.Subject -like "*CN=$caName,*" -and $_.HasPrivateKey} | Select-Object -First 1
if(-not $ca){throw 'Lab root CA certificate not found'}
[IO.File]::WriteAllBytes('C:\Pafta\root-ca.cer',$ca.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))
$leaf=[Security.Cryptography.X509Certificates.X509Certificate2]::new('C:\Pafta\ldaps.cer')
$source="HKLM:\SOFTWARE\Microsoft\SystemCertificates\MY\Certificates\$($leaf.Thumbprint)"
$destination='HKLM:\SOFTWARE\Microsoft\Cryptography\Services\NTDS\SystemCertificates\MY\Certificates'
New-Item -Path $destination -Force | Out-Null
# Copy just this managed leaf's Windows certificate properties, preserving its
# existing machine-key association. Old certificates remain untouched.
Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
$parameters='HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Parameters'
New-ItemProperty -Path $parameters -Name LDAPServerIntegrity -Value 2 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $parameters -Name LdapEnforceChannelBinding -Value 2 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Diagnostics' -Name '16 LDAP Interface Events' -Value 2 -PropertyType DWord -Force | Out-Null
'ldaps-certificate-and-policies-ready'
