param([Parameter(Mandatory=$true)][string]$LabPassword,
      [Parameter(Mandatory=$true)][string]$Address,
      [Parameter(Mandatory=$true)][string]$DcAddress)
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ne 'PF-APP01') { throw 'This script only runs in the managed PF-APP01 lab guest.' }
Install-WindowsFeature RSAT-AD-PowerShell | Out-Null
$nic = Get-NetAdapter | Where-Object Status -eq Up | Select-Object -First 1
Set-NetIPInterface -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -Dhcp Disabled
if(-not (Get-NetIPAddress -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue|Where-Object IPAddress -eq $Address)){
 Get-NetIPAddress -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false
 New-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress $Address -PrefixLength 24 | Out-Null
}
for($attempt=0;$attempt -lt 30;$attempt++){
 if((Get-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress $Address).AddressState -eq 'Preferred'){break}
 Start-Sleep -Seconds 1
}
Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses $DcAddress
Clear-DnsClientCache
$null=Resolve-DnsName _ldap._tcp.dc._msdcs.pafta.test -Type SRV -Server $DcAddress
$password = ConvertTo-SecureString $LabPassword -AsPlainText -Force
$credential = New-Object Management.Automation.PSCredential ('PAFTA\Administrator',$password)
Add-Computer -DomainName pafta.test -Server PF-DC01.pafta.test -Credential $credential -Force
'domain-joined'
