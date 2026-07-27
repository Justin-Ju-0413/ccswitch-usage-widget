# CC Switch Usage Widget - publish to GitHub
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File C:\Users\GSTAR\dev\ccswitch-widget\publish.ps1
$ErrorActionPreference = 'Stop'
$gh = Join-Path $env:USERPROFILE 'dev\gh-bin\bin\gh.exe'
if (-not (Test-Path $gh)) { Write-Error "gh not found: $gh"; exit 1 }
Set-Location $PSScriptRoot

Write-Host "=== 1. gh auth login (authorize in browser) ===" -ForegroundColor Cyan
& $gh auth login

Write-Host "=== 2. create public repo and push ===" -ForegroundColor Cyan
& $gh repo create ccswitch-usage-widget --public --source=. --push

Write-Host "=== 3. push tag v1.1.0 ===" -ForegroundColor Cyan
git push origin v1.1.0

Write-Host "=== Done. Opening repo in browser... ===" -ForegroundColor Green
& $gh repo view --web
