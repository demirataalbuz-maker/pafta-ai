param([Parameter(Mandatory=$true)][string]$Folder, [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
# Windows' own IMAPI creates the unattended seed; no ISO-building package needed.
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class PaftaIso {
    public static void Save(object source, string path) {
        IStream stream = (IStream) source;
        IntPtr count = Marshal.AllocHGlobal(4);
        try {
            byte[] buffer = new byte[65536];
            using (FileStream output = new FileStream(path, FileMode.CreateNew)) {
                while (true) {
                    stream.Read(buffer, buffer.Length, count);
                    int length = Marshal.ReadInt32(count);
                    if (length == 0) break;
                    output.Write(buffer, 0, length);
                }
            }
        } finally { Marshal.FreeHGlobal(count); }
    }
}
'@
$image = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
$image.ChooseImageDefaultsForMediaType(12)
$image.FileSystemsToCreate = 3
$image.VolumeName = 'PAFTASEED'
$image.Root.AddTree((Resolve-Path -LiteralPath $Folder).Path, $false)
$result = $image.CreateResultImage()
[PaftaIso]::Save($result.ImageStream, $Output)
