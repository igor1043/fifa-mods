[CmdletBinding()]
param([string]$PackageRoot)
$ErrorActionPreference = 'Stop'
if (-not $PackageRoot) { $PackageRoot=Join-Path $PSScriptRoot '..\..\..' }
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
    if ($enabledModules.ContainsKey($module) -and -not ($module -eq 'subson' -and $entry -in @('subson\subson_bridge.dll','subson\subson_match_gate_v5.dll'))) { throw "Mais de uma DLL habilitada no mod: $module" }
    $enabledModules[$module] = $true
}
# Original WorkLab SubsOn replaces the retired local bench implementation.
if ($entries -contains 'subson\subson_bridge.dll') {
    foreach ($relative in @('SubsOn.dll','SubsOn.ini','ModCarrerMode\data\catalogs\subson_assets.json')) { Require-File $relative }
    $subsonAsset=Get-Content -LiteralPath (Join-Path $root 'ModCarrerMode\data\catalogs\subson_assets.json') -Raw | ConvertFrom-Json
    if ($subsonAsset.files.Count -ne 1 -or $subsonAsset.files[0].path -ne 'data/ant.cbac' -or
        $subsonAsset.files[0].sha256 -notmatch '^[a-fA-F0-9]{64}$' -or $subsonAsset.files[0].bytes -le 0) { throw 'Manifesto do complemento SubsOn invalido.' }
    if (Test-Path -LiteralPath (Join-Path $mods 'bench_native12')) { throw 'Banco antigo bench_native12 presente junto com SubsOn.' }
}
# Check disabled files too: ignoring them in enabled.txt does not remove them
# from the downloaded package or from a subsequent installation.
foreach ($file in Get-ChildItem -LiteralPath $mods -Recurse -File) {
    if ($file.FullName -match '[\\/]_local_[^\\/]+[\\/]') { continue }
    if ($file.Extension -eq '.bak' -or $file.Name -like '*.before-*' -or ($file.Name -match '_v\d+(?:_\d+)*\.dll$' -and -not $seen.ContainsKey($file.FullName))) { throw "Revisao antiga/backup na pasta de mods: $($file.FullName)" }
}
foreach ($directory in Get-ChildItem -LiteralPath $mods -Directory) {
    if ($directory.Name.StartsWith('_local_')) { continue }
    if ($directory.Name -match '_v\d+$') { throw "Pasta de mod versionada: $($directory.Name)" }
    $moduleDlls=@(Get-ChildItem -LiteralPath $directory.FullName -Recurse -File -Filter '*.dll')
    $subsonPair=$directory.Name -eq 'subson' -and $moduleDlls.Count -eq 2 -and @($moduleDlls | Where-Object { $_.Name -notin @('subson_bridge.dll','subson_match_gate_v5.dll') }).Count -eq 0
    if ($moduleDlls.Count -gt 1 -and -not $subsonPair) { throw "Mais de uma DLL no pacote do mod: $($directory.Name)" }
}
if (@($entries | Where-Object { $_ -match '^mascot_single[\\/]' }).Count) {
    Require-File 'ModCarrerMode\config\match_presentation.ini'
}
if ($entries -contains 'stadium_pyrotechnics\stadium_pyrotechnics.dll') {
    foreach ($relative in @('ModCarrerMode\mods\stadium_pyrotechnics\pyro.ini','ModCarrerMode\config\match_presentation.ini','data\sceneassets\particles\stadium_pyrotechnics_0.lnx','data\sceneassets\particles\stadium_pyrotechnics_0.rx3')) { Require-File $relative }
}
if ($entries -contains 'entrance_props\entrance_props.dll') {
    # Competition IDs come from the game-owned FSW/settings.ini at runtime.
    Require-File 'ModCarrerMode\config\match_presentation.ini'
}
if ($entries -contains 'var_cabin\var_cabin.dll') {
    Require-File 'ModCarrerMode\mods\var_cabin\var_cabin.lua'
    Require-File 'ModCarrerMode\mods\var_cabin\var_cabin.ini'
    $entranceIndex=[Array]::IndexOf($entries,'entrance_props\entrance_props.dll')
    $varIndex=[Array]::IndexOf($entries,'var_cabin\var_cabin.dll')
    if ($entranceIndex -ge 0 -and $varIndex -lt $entranceIndex) { throw 'Os objetos de abertura devem ser carregados antes da cabine do VAR.' }
}
if ($entries -contains 'multiball_visual\multiball_visual.dll') {
    Require-File 'ModCarrerMode\mods\multiball_visual\standball.lua'
    Require-File 'ModCarrerMode\mods\multiball_visual\standball.ini'
    # Stand models/textures are installed locally and excluded from Git.
    # The module keeps the 13 balls on the ground when those assets are absent.
}
if ($entries -contains 'smoke_machine\smoke_machine.dll') {
    foreach ($relative in @('ModCarrerMode\mods\smoke_machine\smoke_machine.ini','ModCarrerMode\mods\smoke_machine\smoke_machine.lua','data\sceneassets\smoke_machine\model.rx3','data\sceneassets\smoke_machine\textures.rx3')) { Require-File $relative }
    if ($entries -notcontains 'stadium_pyrotechnics\stadium_pyrotechnics.dll') { throw 'A máquina de fumaça precisa do módulo stadium_pyrotechnics para os disparos.' }
}
if ($enabledModules.ContainsKey('frontend_stadium')) {
    foreach ($relative in @('ModCarrerMode\tools\frontend_stadium_prepare.exe','ModCarrerMode\config\frontend_stadium.ini',
        'ModCarrerMode\data\catalogs\club_stadium_fallback.tsv','data\fifarna\lua\assets\stadium.lua',
        'data\fifarna\lua\assets\crowd.lua','data\fifarna\lua\assets\server16_frontend_stadium.lua',
        'data\fifarna\lua\assets\server16_frontend_176.lua','data\fifarna\lua\assets\server16_frontend_261.lua',
        'data\ui\game\background\backgroundfifa.big','data\ui\game\screens\misc\stadiumpan.big',
        'data\ui\nav\mainfeflow.nav','data\ui\nav\careermode\mainmenuhubflow.nav',
        'data\ui\imgAssets\backgroundstadiums\st_server16_frontend_clear.dds')) { Require-File $relative }
}
if ($enabledModules.ContainsKey('panorama_drone')) { Require-File 'ModCarrerMode\config\panorama_drone.ini' }
if ($enabledModules.ContainsKey('club_environment')) {
    foreach ($relative in @('ModCarrerMode\source\club_environment\portable_paths.py',
        'ModCarrerMode\source\club_environment\assets-manifest.json',
        'ModCarrerMode\source\club_environment\room\prepare_native_room_components_r46_20261022.py',
        'ModCarrerMode\source\club_environment\bank\watch_r57.py',
        'ModCarrerMode\source\club_environment\preview\prepare.py',
        'data\ui\nav\careermode\server16dressingroomflow.nav',
        'data\ui\nav\careermode\server16bankloansflow.nav',
        'data\ui\nav\careermode\server16matchpreviewflow.nav')) { Require-File $relative }
}
if ($enabledModules.ContainsKey('extra_scenes')) { Require-File 'ModCarrerMode\config\extra_scenes.ini' }
[pscustomobject]@{Package=$root;Verified=$true;EnabledPlugins=$entries.Count;MascotModels='Local packages required; excluded from Git'}
