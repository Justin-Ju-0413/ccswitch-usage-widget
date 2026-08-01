# Build a local TokenTicker release candidate. This script never pushes or moves tags.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

python -m unittest discover -s tests -v
python -m PyInstaller --clean --onefile --noconsole --name TokenTicker --collect-all customtkinter ccswitch_widget.py

$artifact = Join-Path $PSScriptRoot 'dist\TokenTicker.exe'
if (-not (Test-Path $artifact)) { throw "Missing build artifact: $artifact" }
$hash = Get-FileHash $artifact -Algorithm SHA256
$checksumPath = "$artifact.sha256"
"$($hash.Hash.ToLower())  TokenTicker.exe" | Set-Content -Encoding ascii $checksumPath

Write-Output "artifact = $artifact"
Write-Output "sha256  = $($hash.Hash.ToLower())"
Write-Output "Release remains local until tag and GitHub Release authorization is granted."
