function Test-PaftaWriteDacl {
    param([ValidateSet('ali.kaya','mehmet.yilmaz','pf_s4u_user')][string]$User)
    if($env:COMPUTERNAME -ne 'PF-DC01'){throw 'Managed PF-DC01 guest required.'}
    if(-not ('PaftaNativeAccess' -as [type])){
        Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public static class PaftaNativeAccess {
 [StructLayout(LayoutKind.Sequential)] struct Mapping {public uint Read,Write,Execute,All;}
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool LogonUser(string u,string d,string p,int t,int provider,out IntPtr token);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool AccessCheck(byte[] sd,IntPtr token,uint desired,ref Mapping map,IntPtr priv,ref uint length,out uint granted,out bool allowed);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 public static bool Check(byte[] sd,string user,string password){
  IntPtr token;
  if(!LogonUser(user,"PAFTA",password,3,0,out token))throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
  IntPtr priv=Marshal.AllocHGlobal(1024);
  try {
   Mapping map=new Mapping {Read=0x20094,Write=0x20028,Execute=0x20004,All=0xf01ff};
   uint length=1024,granted;bool allowed;
   if(!AccessCheck(sd,token,0x40000,ref map,priv,ref length,out granted,out allowed))throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   return allowed;
  } finally {Marshal.FreeHGlobal(priv);CloseHandle(token);}
 }
}
'@
    }
    Import-Module ActiveDirectory
    $dn=(Get-ADUser svc_sql).DistinguishedName
    $entry=[DirectoryServices.DirectoryEntry]::new("LDAP://localhost/$dn")
    $entry.psbase.AuthenticationType=[DirectoryServices.AuthenticationTypes]::Secure -bor [DirectoryServices.AuthenticationTypes]::Signing -bor [DirectoryServices.AuthenticationTypes]::Sealing
    $entry.get_Options().SecurityMasks=[DirectoryServices.SecurityMasks]::Owner -bor [DirectoryServices.SecurityMasks]::Group -bor [DirectoryServices.SecurityMasks]::Dacl
    try {$binary=$entry.psbase.ObjectSecurity.GetSecurityDescriptorBinaryForm()} finally {$entry.psbase.Dispose()}
    $secret=Get-Content -Raw C:\Pafta\lab-secret.json|ConvertFrom-Json
    [PaftaNativeAccess]::Check($binary,$User,$secret.password)
}
