# CMD yolunun Sysinternals araçlarını (sigcheck64, autorunsc64) .deps\sysinternals'a kurar; CMD koşucusu orayı PATH'e ekler.
# download.sysinternals.com her zaman son sürümü verir; bu yüzden sürüm URL'den değil, indirilen dosyadan doğrulanır.
# İmza Microsoft'un kod imzalama sertifikasıyla geçerli değilse ya da sürüm beklenenden farklıysa kurulmaz.
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File tools\sysinternals_kur.ps1
$ErrorActionPreference = 'Stop'
$beklenen = @{ 'sigcheck64.exe' = '2.93'; 'autorunsc64.exe' = '14.3' }
$imzaci = 'AB172913A2960A224809EE8A0C371CD47A079B72'   # CN=Microsoft Corporation (24 Ekim 2026'da ölçüldü)

$kok = Split-Path -Parent $PSScriptRoot
$hedef = Join-Path $kok '.deps\sysinternals'
if ((Test-Path (Join-Path $hedef 'sigcheck64.exe')) -and (Test-Path (Join-Path $hedef 'autorunsc64.exe'))) {
    "Sysinternals araçları zaten kurulu: $hedef"
    return
}
$gecici = Join-Path $env:TEMP ('sysint_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $gecici | Out-Null
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    foreach ($paket in 'Sigcheck', 'Autoruns') {
        $zip = Join-Path $gecici "$paket.zip"
        Invoke-WebRequest -UseBasicParsing -Uri "https://download.sysinternals.com/files/$paket.zip" -OutFile $zip
        [IO.Compression.ZipFile]::ExtractToDirectory($zip, (Join-Path $gecici $paket))
    }
    New-Item -ItemType Directory $hedef -Force | Out-Null
    foreach ($ad in $beklenen.Keys) {
        $dosya = Get-ChildItem $gecici -Recurse -Filter $ad | Select-Object -First 1
        $imza = Get-AuthenticodeSignature -LiteralPath $dosya.FullName
        if ($imza.Status -ne 'Valid' -or $imza.SignerCertificate.Thumbprint -ne $imzaci) {
            throw "$ad imzası beklenen gibi değil: $($imza.Status) $($imza.SignerCertificate.Thumbprint)"
        }
        if ($dosya.VersionInfo.FileVersion -ne $beklenen[$ad]) {
            throw "$ad sürümü $($dosya.VersionInfo.FileVersion); beklenen $($beklenen[$ad]). Dersler bu sürümle ölçüldü; yeni sürümü önce denetle."
        }
        Copy-Item $dosya.FullName $hedef -Force
    }
    Copy-Item (Get-ChildItem $gecici -Recurse -Filter 'Eula.txt' | Select-Object -First 1).FullName $hedef -Force
    "Sysinternals araçları kuruldu: $hedef"
} finally {
    Remove-Item $gecici -Recurse -Force -ErrorAction SilentlyContinue
}
