$ErrorActionPreference='Stop'
if($env:COMPUTERNAME -ne 'PF-DC01'){throw 'Managed PF-DC01 guest required.'}
Import-Module ActiveDirectory
Import-Module ADCSAdministration
$config=(Get-ADRootDSE).configurationNamingContext
$base="CN=Certificate Templates,CN=Public Key Services,CN=Services,$config"
$source=Get-ADObject -Identity "CN=User,$base" -Properties *
$enroll=[guid]'0e10c968-78fb-11d2-90d4-00c04f79dc55'
$sid=(Get-ADGroup 'Domain Users').SID
$specs=@(
    @{Name='PaftaClientLegacy';NameFlags=1;EnrollmentFlags=0;Signatures=0;Client=$true;Published=$true;Edit=$false},
    @{Name='PaftaClientPending';NameFlags=1;EnrollmentFlags=2;Signatures=0;Client=$true;Published=$true;Edit=$false},
    @{Name='PaftaClientSigned';NameFlags=1;EnrollmentFlags=0;Signatures=1;Client=$true;Published=$true;Edit=$false},
    @{Name='PaftaServerOnly';NameFlags=1;EnrollmentFlags=0;Signatures=0;Client=$false;Published=$true;Edit=$false},
    @{Name='PaftaClientDraft';NameFlags=1;EnrollmentFlags=0;Signatures=0;Client=$true;Published=$false;Edit=$false},
    @{Name='PaftaClientEditable';NameFlags=0;EnrollmentFlags=0;Signatures=0;Client=$true;Published=$true;Edit=$true}
)
foreach($s in $specs){
    $dn="CN=$($s.Name),$base"
    if(-not (Get-ADObject -LDAPFilter "(cn=$($s.Name))" -SearchBase $base)){
        $attrs=@{}
        foreach($key in @('flags','revision','pKIDefaultKeySpec','pKIKeyUsage','pKIMaxIssuingDepth','pKICriticalExtensions','pKIExpirationPeriod','pKIOverlapPeriod','pKIDefaultCSPs','msPKI-Minimal-Key-Size','msPKI-Private-Key-Flag')){
            $value=$source.$key
            if($null -ne $value -and $value.Count -gt 0){$attrs[$key]=$value}
        }
        $eku=if($s.Client){'1.3.6.1.5.5.7.3.2'}else{'1.3.6.1.5.5.7.3.1'}
        $attrs['displayName']=$s.Name
        $attrs['msPKI-Template-Schema-Version']=[int]2
        $attrs['msPKI-Template-Minor-Revision']=[int]1
        $attrs['msPKI-Certificate-Name-Flag']=[int]$s.NameFlags
        $attrs['msPKI-Enrollment-Flag']=[int]$s.EnrollmentFlags
        $attrs['msPKI-RA-Signature']=[int]$s.Signatures
        $attrs['pKIExtendedKeyUsage']=@($eku)
        $attrs['msPKI-Certificate-Application-Policy']=@($eku)
        $attrs['msPKI-Cert-Template-OID']='1.3.6.1.4.1.311.21.8.999999.'+(Get-Random -Minimum 1000000 -Maximum 2000000000)
        New-ADObject -Name $s.Name -Type pKICertificateTemplate -Path $base -OtherAttributes $attrs
    }
    $entry=[DirectoryServices.DirectoryEntry]::new("LDAP://localhost/$dn")
    $entry.psbase.AuthenticationType=[DirectoryServices.AuthenticationTypes]::Secure -bor [DirectoryServices.AuthenticationTypes]::Signing -bor [DirectoryServices.AuthenticationTypes]::Sealing
    $entry.psbase.Options.SecurityMasks=[DirectoryServices.SecurityMasks]::Dacl
    $acl=$entry.psbase.ObjectSecurity
    $allow=[Security.AccessControl.AccessControlType]::Allow
    if($s.Edit){
        $ace=[DirectoryServices.ActiveDirectoryAccessRule]::new($sid,[DirectoryServices.ActiveDirectoryRights]::WriteDacl,$allow)
    }else{
        $ace=[DirectoryServices.ActiveDirectoryAccessRule]::new($sid,[DirectoryServices.ActiveDirectoryRights]::ExtendedRight,$allow,$enroll)
    }
    $acl.AddAccessRule($ace)
    $entry.psbase.ObjectSecurity=$acl
    $entry.psbase.CommitChanges()
    $entry.psbase.Dispose()
}
foreach($s in $specs){
    if($s.Published){
        $caName=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\CertSvc\Configuration').Active
        for($attempt=0;$attempt -lt 10;$attempt++){
            $message=& certutil.exe -config "PF-DC01\$caName" -SetCATemplates ("+"+$s.Name) 2>&1
            if($LASTEXITCODE -eq 0){break}
            Start-Sleep -Seconds 2
        }
        if($LASTEXITCODE -ne 0){throw "CA publish failed: $($s.Name): $message"}
    }
}
Restart-Service CertSvc
'six-real-ad-templates-ready'
