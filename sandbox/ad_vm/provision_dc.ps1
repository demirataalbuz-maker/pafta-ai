param([Parameter(Mandatory=$true)][string]$Stage,
      [Parameter(Mandatory=$true)][string]$LabPassword,
      [Parameter(Mandatory=$true)][string]$Address)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'PF-DC01') { throw 'This script only runs in the managed PF-DC01 lab guest.' }
if ($Stage -eq 'forest') {
    $nic = Get-NetAdapter | Where-Object Status -eq Up | Select-Object -First 1
    Set-NetIPInterface -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -Dhcp Disabled
    Get-NetIPAddress -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false
    New-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress $Address -PrefixLength 24 | Out-Null
    for($attempt=0;$attempt -lt 30;$attempt++){
        if((Get-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress $Address).AddressState -eq 'Preferred'){break}
        Start-Sleep -Seconds 1
    }
    Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses 127.0.0.1
    Install-WindowsFeature AD-Domain-Services -IncludeManagementTools | Out-Null
    Import-Module ADDSDeployment
    $safe = ConvertTo-SecureString $LabPassword -AsPlainText -Force
    Install-ADDSForest -DomainName pafta.test -DomainNetbiosName PAFTA -InstallDns:$true -SafeModeAdministratorPassword $safe -NoRebootOnCompletion:$true -Force:$true | Out-Null
    'forest-installed'
    exit
}
if ($Stage -ne 'directory') { throw 'Unknown provisioning stage.' }
Import-Module ActiveDirectory
$base = 'DC=pafta,DC=test'
if (-not (Get-ADOrganizationalUnit -Filter 'Name -eq "PaftaLab"')) {
    New-ADOrganizationalUnit -Name PaftaLab -Path $base -ProtectedFromAccidentalDeletion:$false
}
$ou = "OU=PaftaLab,$base"
$safe = ConvertTo-SecureString $LabPassword -AsPlainText -Force
@{password=$LabPassword}|ConvertTo-Json|Set-Content C:\Pafta\lab-secret.json -Encoding UTF8
& icacls.exe C:\Pafta\lab-secret.json /inheritance:r /grant:r 'SYSTEM:F' 'PAFTA\Domain Admins:F' | Out-Null
foreach ($name in @('ali.kaya','mehmet.yilmaz','svc_sql','pf_s4u_user')) {
    if (-not (Get-ADUser -Filter "SamAccountName -eq '$name'")) {
        New-ADUser -Name $name -SamAccountName $name -UserPrincipalName "$name@pafta.test" -Path $ou -AccountPassword $safe -Enabled:$true -PasswordNeverExpires:$true
    }
}
if (-not (Get-ADGroup -Filter 'Name -eq "SOC-Analistleri"')) {
    New-ADGroup -Name SOC-Analistleri -GroupScope Global -Path $ou
}
Add-ADGroupMember SOC-Analistleri -Members ali.kaya,mehmet.yilmaz
$dn = (Get-ADUser svc_sql).DistinguishedName
$entry = [DirectoryServices.DirectoryEntry]::new("LDAP://localhost/$dn")
$entry.psbase.AuthenticationType = [DirectoryServices.AuthenticationTypes]::Secure -bor [DirectoryServices.AuthenticationTypes]::Signing -bor [DirectoryServices.AuthenticationTypes]::Sealing
$entry.psbase.Options.SecurityMasks = [DirectoryServices.SecurityMasks]::Dacl
$sd = $entry.psbase.ObjectSecurity
$right = [DirectoryServices.ActiveDirectoryRights]::WriteDacl
$allow = [Security.AccessControl.AccessControlType]::Allow
$deny = [Security.AccessControl.AccessControlType]::Deny
$sd.AddAccessRule((New-Object DirectoryServices.ActiveDirectoryAccessRule ((Get-ADGroup SOC-Analistleri).SID,$right,$allow)))
$sd.AddAccessRule((New-Object DirectoryServices.ActiveDirectoryAccessRule ((Get-ADUser mehmet.yilmaz).SID,$right,$deny)))
$entry.psbase.ObjectSecurity = $sd
$entry.psbase.CommitChanges()
$entry.psbase.Dispose()
# All proof resources are inside this throwaway lab, not on the host.
New-Item C:\Pafta\proof -ItemType Directory -Force | Out-Null
[IO.File]::WriteAllText('C:\Pafta\proof\proof.txt', 'Pafta S4U proof', (New-Object Text.UTF8Encoding $false))
if (-not (Get-SmbShare -Name PaftaRead -ErrorAction SilentlyContinue)) {
    New-SmbShare -Name PaftaRead -Path C:\Pafta\proof -ReadAccess 'PAFTA\pf_s4u_user' | Out-Null
}
& icacls.exe C:\Pafta\proof /grant 'PAFTA\pf_s4u_user:(OI)(CI)RX' | Out-Null
# Language-independent audit subcategory GUID: Kerberos Service Ticket Operations.
& auditpol.exe /set '/subcategory:{0CCE9240-69AE-11D9-BED3-505054503030}' /success:enable /failure:enable | Out-Null
Install-WindowsFeature ADCS-Cert-Authority -IncludeManagementTools | Out-Null
Import-Module ADCSDeployment
if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Services\CertSvc\Configuration\Pafta-Lab-CA')) {
    Install-AdcsCertificationAuthority -CAType EnterpriseRootCA -CACommonName Pafta-Lab-CA -CryptoProviderName 'RSA#Microsoft Software Key Storage Provider' -KeyLength 2048 -HashAlgorithmName SHA256 -ValidityPeriod Years -ValidityPeriodUnits 2 -Force | Out-Null
}
'directory-and-ca-ready'
