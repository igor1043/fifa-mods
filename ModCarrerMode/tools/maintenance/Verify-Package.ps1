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
foreach ($entry in $entries) {
    $target = [IO.Path]::GetFullPath((Join-Path $mods $entry))
    if (-not $target.StartsWith($mods+'\',[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($target) -ne '.dll') { throw "Entrada de plugin invalida: $entry" }
    if ($seen.ContainsKey($target)) { throw "Plugin duplicado: $entry" }
    $seen[$target] = $true
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "DLL habilitada ausente: $entry" }
}
foreach ($pattern in @('^mascot_single[\\/]','^kickoff_modern(?:_v\d+)?[\\/]')) {
    if (@($entries | Where-Object { $_ -match $pattern }).Count -gt 1) { throw 'Mais de uma DLL de mascote ou kickoff habilitada.' }
}
if (@($entries | Where-Object { $_ -match '^mascot_single[\\/]' }).Count) {
    Require-File 'ModCarrerMode\config\match_presentation.ini'
}
if ($entries -contains 'stadium_pyrotechnics\stadium_pyrotechnics.dll') {
    foreach ($relative in @('ModCarrerMode\mods\stadium_pyrotechnics\pyro.ini','ModCarrerMode\config\match_presentation.ini','data\sceneassets\particles\stadium_pyrotechnics_0.lnx','data\sceneassets\particles\stadium_pyrotechnics_0.rx3')) { Require-File $relative }
}
[pscustomobject]@{Package=$root;Verified=$true;EnabledPlugins=$entries.Count;MascotModels='Local packages required; excluded from Git'}
