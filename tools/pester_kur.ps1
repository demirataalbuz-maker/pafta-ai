# Pester 5.9.0'ı proje kapsamına (.deps\psmodules) kurar; PowerShell koşucusu orayı önce arar.
# İndirilen paket SHA-256 ile, modül dosyaları Authenticode imzası ve imzalayan parmak iziyle doğrulanır.
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File tools\pester_kur.ps1
$ErrorActionPreference = 'Stop'
$surum = '5.9.0'
$beklenenOzet = '5A0FD80B361600BF4BBD4C307C1FD01B17F11668BAB19E657ADD41B00AD22AB9'
$beklenenImzaci = '147C2FD397677DC76DD198E83E7D9D234AA59D1A'   # CN=Jakub Jareš (Pester bakımcısı)

$kok = Split-Path -Parent $PSScriptRoot
$hedef = Join-Path $kok ".deps\psmodules\Pester\$surum"
if (Test-Path (Join-Path $hedef 'Pester.psd1')) {
    "Pester $surum zaten kurulu: $hedef"
    return
}
$gecici = Join-Path $env:TEMP ("pester_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $gecici | Out-Null
try {
    $paket = Join-Path $gecici "pester.$surum.nupkg"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.powershellgallery.com/api/v2/package/Pester/$surum" -OutFile $paket
    $ozet = (Get-FileHash $paket -Algorithm SHA256).Hash
    if ($ozet -ne $beklenenOzet) { throw "Paket özeti tutmuyor: $ozet" }
    $acik = Join-Path $gecici 'acik'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($paket, $acik)
    foreach ($dosya in 'Pester.psd1', 'Pester.psm1') {
        $imza = Get-AuthenticodeSignature -LiteralPath (Join-Path $acik $dosya)
        if ($imza.Status -ne 'Valid' -or $imza.SignerCertificate.Thumbprint -ne $beklenenImzaci) {
            throw "$dosya imzası beklenen gibi değil: $($imza.Status) $($imza.SignerCertificate.Thumbprint)"
        }
    }
    New-Item -ItemType Directory $hedef -Force | Out-Null
    Get-ChildItem $acik | Where-Object { $_.Name -notin '_rels', 'package', '[Content_Types].xml', 'Pester.nuspec' } |
        Copy-Item -Destination $hedef -Recurse -Force
    "Pester $surum kuruldu: $hedef"
} finally {
    Remove-Item $gecici -Recurse -Force -ErrorAction SilentlyContinue
}
