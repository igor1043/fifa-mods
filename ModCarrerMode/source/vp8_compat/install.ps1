param([string]$GameDirectory = 'U:\fifa 16')
$ErrorActionPreference = 'Stop'
$gameRoot = (Resolve-Path -LiteralPath $GameDirectory).Path
if (!(Test-Path -LiteralPath (Join-Path $gameRoot 'fifa16.exe'))) { throw 'FIFA installation not found.' }
if (Get-Process -Name fifa16 -ErrorAction SilentlyContinue) { throw 'Close FIFA before installation.' }
$package = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\mods\vp8_compat'))
$builtDll = Join-Path $PSScriptRoot 'build\vp8_compat.dll'
$candidate = Join-Path $package 'test_1080p_high.vp8'
if (!(Test-Path -LiteralPath $builtDll) -or !(Test-Path -LiteralPath $candidate)) { throw 'Build and convert first.' }
Copy-Item -LiteralPath $builtDll -Destination (Join-Path $package 'vp8_compat.dll')
$modsRoot = Join-Path $gameRoot 'ModCarrerMode\mods'
if (!(Test-Path -LiteralPath (Join-Path $modsRoot 'mod_host.dll'))) { throw 'Existing mod host is required.' }
$backupRoot = Join-Path $gameRoot ('runtime\vp8_install_backup_' + (Get-Date -Format yyyyMMdd_HHmmss))
New-Item -ItemType Directory -Path $backupRoot | Out-Null
$enabled = Join-Path $modsRoot 'enabled.txt'
Copy-Item -LiteralPath $enabled -Destination (Join-Path $backupRoot 'enabled.txt')
if ((Get-FileHash -LiteralPath $enabled).Hash -ne (Get-FileHash -LiteralPath (Join-Path $backupRoot 'enabled.txt')).Hash) { throw 'Backup mismatch.' }
$destination = Join-Path $modsRoot 'vp8_compat'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
foreach ($name in @('vp8_compat.dll','test_1080p_high.vp8','README.md','disable.ps1')) {
    $sourceFile = Join-Path $package $name
    if (!(Test-Path -LiteralPath $sourceFile)) { continue }
    $targetFile = Join-Path $destination $name
    if (Test-Path -LiteralPath $targetFile) {
        Copy-Item -LiteralPath $targetFile -Destination (Join-Path $backupRoot $name)
    }
    Copy-Item -LiteralPath $sourceFile -Destination $targetFile
    if ((Get-FileHash -LiteralPath $sourceFile).Hash -ne (Get-FileHash -LiteralPath $targetFile).Hash) { throw 'Install mismatch.' }
}
$line = 'vp8_compat\vp8_compat.dll'
if (@(Get-Content -LiteralPath $enabled) -notcontains $line) { Add-Content -LiteralPath $enabled -Value "`r`n$line" -Encoding utf8 }
Write-Output "Installed experimental plugin. Backup: $backupRoot"
