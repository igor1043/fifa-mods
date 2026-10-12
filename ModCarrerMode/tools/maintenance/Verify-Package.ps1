[CmdletBinding()]
param([string]$PackageRoot = (Join-Path $PSScriptRoot '..\..\..'))
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $PackageRoot).Path.TrimEnd('\')
$mods = Join-Path $root 'ModCarrerMode\mods'
function Require-File([string]$Relative) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $Relative) -PathType Leaf)) {
        throw "Arquivo ausente no pacote: $Relative"
    }
}
foreach ($relative in @('dinput8.dll','dinput8_orig.dll','dinput8_L9.ini','dinput8_patch.ini','winmm.dll','Server16Python.exe','ModCarrerMode\retirement_offline_worker.exe','ModCarrerMode\mods\mod_host.dll','ModCarrerMode\mods\enabled.txt','data\fifarna\lua\assets\sle.lua')) {
    Require-File $relative
}
$entries = @(Get-Content -LiteralPath (Join-Path $mods 'enabled.txt') | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
$seen = @{}
$enabledModules = @{}
foreach ($entry in $entries) {
    $target = [IO.Path]::GetFullPath((Join-Path $mods $entry))
    if (-not $target.StartsWith($mods+'\',[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($target) -ne '.dll') { throw "Entrada de plugin invalida: $entry" }
    if ($seen.ContainsKey($target)) { throw "Plugin duplicado: $entry" }
    $seen[$target] = $true
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "DLL habilitada ausente: $entry" }
    $module = ($entry -split '[\\/]')[0]
    if ($enabledModules.ContainsKey($module)) { throw "Mais de uma DLL habilitada no mod: $module" }
    $enabledModules[$module] = $true
}
# Check disabled files too: ignoring them in enabled.txt does not remove them
# from the downloaded package or from a subsequent installation.
foreach ($file in Get-ChildItem -LiteralPath $mods -Recurse -File) {
    if ($file.Extension -eq '.bak' -or $file.Name -match '_v\d+\.dll$') { throw "Revisao antiga/backup na pasta de mods: $($file.FullName)" }
}
foreach ($directory in Get-ChildItem -LiteralPath $mods -Directory) {
    if ($directory.Name -match '_v\d+$') { throw "Pasta de mod versionada: $($directory.Name)" }
    if (@(Get-ChildItem -LiteralPath $directory.FullName -Recurse -File -Filter '*.dll').Count -gt 1) { throw "Mais de uma DLL no pacote do mod: $($directory.Name)" }
}
if (@($entries | Where-Object { $_ -match '^mascot_single[\\/]' }).Count) {
    Require-File 'ModCarrerMode\config\match_presentation.ini'
}
if ($entries -contains 'stadium_pyrotechnics\stadium_pyrotechnics.dll') {
    foreach ($relative in @('ModCarrerMode\mods\stadium_pyrotechnics\pyro.ini','ModCarrerMode\config\match_presentation.ini','data\sceneassets\particles\stadium_pyrotechnics_0.lnx','data\sceneassets\particles\stadium_pyrotechnics_0.rx3')) { Require-File $relative }
}
[pscustomobject]@{Package=$root;Verified=$true;EnabledPlugins=$entries.Count;MascotModels='Local packages required; excluded from Git'}
