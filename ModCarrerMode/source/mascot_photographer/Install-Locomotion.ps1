param([string]$GameRoot = 'U:\fifa 16')
$ErrorActionPreference = 'Stop'
if (Get-Process -Name fifa16 -ErrorAction SilentlyContinue) {
    throw 'Feche o FIFA antes de instalar: a DLL anterior continua carregada na partida aberta.'
}
$taskProject = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$taskGame = (Resolve-Path -LiteralPath $GameRoot).Path
$taskDllName = 'mascot_goal_line_v22.dll'
$taskDllSource = Join-Path $taskProject ('ModCarrerMode\mods\mascot_single\' + $taskDllName)
$taskDllTarget = Join-Path $taskGame ('ModCarrerMode\mods\mascot_single\' + $taskDllName)
if (-not (Test-Path -LiteralPath (Join-Path $taskGame 'fifa16.exe'))) { throw 'A pasta de destino nao contem fifa16.exe.' }
if (-not (Test-Path -LiteralPath $taskDllSource)) { throw 'Compile com build.cmd antes de instalar.' }
$taskBackup = Join-Path $taskGame ('ModCarrerMode\backups\mascot_locomotion_install_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $taskBackup -Force | Out-Null
if (Test-Path -LiteralPath $taskDllTarget) { Copy-Item -LiteralPath $taskDllTarget -Destination (Join-Path $taskBackup ($taskDllName + '.before')) }
New-Item -ItemType Directory -Path (Split-Path -Parent $taskDllTarget) -Force | Out-Null
Copy-Item -LiteralPath $taskDllSource -Destination $taskDllTarget -Force
$taskPackages = Join-Path $taskProject 'data\sceneassets\mascot'
foreach ($taskPackage in Get-ChildItem -LiteralPath $taskPackages -Directory) {
    if ($taskPackage.Name -notmatch '^\d+$') { continue }
    $taskMarker = Join-Path $taskPackage.FullName 'locomotion_feet.bin'
    if (-not (Test-Path -LiteralPath $taskMarker)) { continue }
    $taskModel = Join-Path $taskPackage.FullName 'model_animated.rx3'
    $taskTargetFolder = Join-Path $taskGame ('data\sceneassets\mascot\' + $taskPackage.Name)
    $taskGameModel = Join-Path $taskTargetFolder 'model_animated.rx3'
    if (-not (Test-Path -LiteralPath $taskModel) -or -not (Test-Path -LiteralPath $taskGameModel)) { continue }
    if ((Get-FileHash -LiteralPath $taskModel).Hash -ne (Get-FileHash -LiteralPath $taskGameModel).Hash) {
        Write-Warning ('Marcador nao copiado: modelo diferente no clube ' + $taskPackage.Name)
        continue
    }
    $taskTargetMarker = Join-Path $taskTargetFolder 'locomotion_feet.bin'
    if (Test-Path -LiteralPath $taskTargetMarker) { Copy-Item -LiteralPath $taskTargetMarker -Destination (Join-Path $taskBackup ($taskPackage.Name + '.locomotion_feet.bin.before')) }
    Copy-Item -LiteralPath $taskMarker -Destination $taskTargetMarker -Force
    Write-Output ('Marcadores instalados: ' + $taskPackage.Name)
}
$taskEnabled = Join-Path $taskGame 'ModCarrerMode\mods\enabled.txt'
Copy-Item -LiteralPath $taskEnabled -Destination (Join-Path $taskBackup 'enabled.txt.before')
$taskEnabledLines = @(Get-Content -LiteralPath $taskEnabled)
$taskNewLines = @()
$taskMascotAdded = $false
foreach ($taskLine in $taskEnabledLines) {
    if ($taskLine.Trim() -match '^mascot_single[\\/]mascot_goal_line(?:_v\d+)?\.dll$') {
        if (-not $taskMascotAdded) { $taskNewLines += ('mascot_single\' + $taskDllName); $taskMascotAdded = $true }
    } else { $taskNewLines += $taskLine }
}
if (-not $taskMascotAdded) { $taskNewLines += ('mascot_single\' + $taskDllName) }
Set-Content -LiteralPath $taskEnabled -Value $taskNewLines -Encoding utf8
$taskSourceHash = (Get-FileHash -LiteralPath $taskDllSource).Hash
$taskTargetHash = (Get-FileHash -LiteralPath $taskDllTarget).Hash
if ($taskSourceHash -ne $taskTargetHash) { throw 'A DLL copiada nao corresponde ao desenvolvimento.' }
Write-Output ('DLL instalada e ativada. SHA256=' + $taskTargetHash)
Write-Output ('Backup=' + $taskBackup)
