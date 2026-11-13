# PowerShell yolunun PS29 paftası için PowerShell 7'yi .deps\pwsh\<sürüm> klasörüne kurar.
# Taşınabilir paket kullanılır: yönetici yetkisi, kayıt defteri kaydı, servis ve başlangıç girdisi yok;
# sistemdeki PowerShell'e dokunulmaz. Paket GitHub'daki resmi PowerShell deposundan indirilir ve
# yayımlanan sha256 özetiyle doğrulanır; özet tutmazsa kurulmaz.
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File tools\pwsh7_kur.ps1
$ErrorActionPreference = 'Stop'
$surum = '7.6.8'
$ozet = 'b9f074f923c499b51ec99d313da8e9ae90d17a9f3adf00c73d6189f34d908528'   # PowerShell-7.6.8-win-x64.zip

$kok = Split-Path -Parent $PSScriptRoot
$klasor = Join-Path $kok ".deps\pwsh"
$hedef = Join-Path $klasor $surum
if (Test-Path (Join-Path $hedef 'pwsh.exe')) {
    "PowerShell $surum zaten kurulu: $hedef"
    return
}
New-Item -ItemType Directory $klasor -Force | Out-Null
$zip = Join-Path $klasor "PowerShell-$surum-win-x64.zip"
if (-not (Test-Path $zip)) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $url = "https://github.com/PowerShell/PowerShell/releases/download/v$surum/PowerShell-$surum-win-x64.zip"
    "İndiriliyor (yaklaşık 106 MB): $url"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip
}
$bulunan = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLower()
if ($bulunan -ne $ozet) {
    Remove-Item $zip -Force
    throw "Paketin sha256 özeti beklenenden farklı ($bulunan); kurulmadı."
}
Expand-Archive -LiteralPath $zip -DestinationPath $hedef -Force
$cikan = & (Join-Path $hedef 'pwsh.exe') -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
if ($cikan -ne $surum) { throw "Kurulan sürüm $cikan; beklenen $surum." }
"PowerShell $surum kuruldu: $hedef"
