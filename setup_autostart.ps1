$ErrorActionPreference = 'Stop'
$py = (& python -c "import sys; print(sys.executable)").Trim()
if (-not $py -or -not (Test-Path $py)) { Write-Error "python not found"; exit 1 }
$pyDir = Split-Path $py -Parent
$pythonw = Join-Path $pyDir 'pythonw.exe'
if (-not (Test-Path $pythonw)) { Write-Error "pythonw not found: $pythonw"; exit 1 }
$script = 'C:\Users\GSTAR\dev\ccswitch-widget\ccswitch_widget.py'
$workDir = 'C:\Users\GSTAR\dev\ccswitch-widget'
$startupDir = [Environment]::GetFolderPath('Startup')
$desktopDir = [Environment]::GetFolderPath('Desktop')
$ws = New-Object -ComObject WScript.Shell
$l1 = $ws.CreateShortcut((Join-Path $startupDir 'CC Switch Widget.lnk'))
$l1.TargetPath = $pythonw; $l1.Arguments = $script; $l1.WorkingDirectory = $workDir; $l1.Description = 'CC Switch usage widget'; $l1.Save()
$l2 = $ws.CreateShortcut((Join-Path $desktopDir 'CC Switch Widget.lnk'))
$l2.TargetPath = $pythonw; $l2.Arguments = $script; $l2.WorkingDirectory = $workDir; $l2.Description = 'CC Switch usage widget'; $l2.Save()
Write-Output "pythonw = $pythonw"
Write-Output "startup = $(Join-Path $startupDir 'CC Switch Widget.lnk')"
Write-Output "desktop = $(Join-Path $desktopDir 'CC Switch Widget.lnk')"
Write-Output "done"
