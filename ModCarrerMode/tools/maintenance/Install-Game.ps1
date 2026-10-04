[CmdletBinding()]
param(
    [string]$GameDirectory = 'U:\fifa 16',
    [string]$BackupDirectory = 'J:\mods\backup',
    [switch]$RestoreLocalization,
    [switch]$ReplaceConfiguration,
    [switch]$ArchiveDevelopmentFiles,
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
function Get-Sha256([string]$LiteralPath) {
    $stream = [IO.File]::OpenRead($LiteralPath)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
    finally { $sha.Dispose(); $stream.Dispose() }
}
$modSource = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$repoSource = [IO.Directory]::GetParent($modSource).FullName
$game = (Resolve-Path -LiteralPath $GameDirectory).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $game 'FIFA16.exe'))) { throw 'A pasta selecionada nao contem FIFA16.exe.' }
if ($game -eq $repoSource) { throw 'O destino nao pode ser a pasta Dev.' }
$gameMod = Join-Path $game 'ModCarrerMode'
$editionConfig = Join-Path $modSource 'config\edition.ini'
if (-not (Test-Path -LiteralPath $editionConfig -PathType Leaf)) { throw 'Identificacao da edicao ausente no Dev.' }
$edition = [regex]::Match((Get-Content -LiteralPath $editionConfig -Raw), '(?m)^id=(v12|new-experience)\s*$').Groups[1].Value
if (-not $edition) { throw 'Edicao desconhecida; use o pacote V12 ou New Experience.' }
function Assert-Child([string]$Base,[string]$Target) {
    $baseFull=[IO.Path]::GetFullPath($Base).TrimEnd('\')+'\'
    $targetFull=[IO.Path]::GetFullPath($Target)
    if (-not $targetFull.StartsWith($baseFull,[StringComparison]::OrdinalIgnoreCase)) { throw "Destino fora da pasta: $Target" }
}
$files = [Collections.Generic.List[object]]::new()
function Add-File([string]$Source,[string]$Relative) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Arquivo Dev ausente: $Source" }
    $target=Join-Path $game $Relative;Assert-Child $game $target
    $files.Add([pscustomobject]@{Source=$Source;Relative=$Relative;Target=$target;Hash=(Get-Sha256 $Source)})
}
foreach($name in @('dinput8.dll','dinput8_orig.dll','dinput8_L9.ini','dinput8_patch.ini','winmm.dll','Server16Python.exe')) { Add-File (Join-Path $repoSource $name) $name }
$runtimeFiles = @('retirement_offline_worker.exe','crowd.ini')
if ($edition -eq 'new-experience') { $runtimeFiles += 'career_operations_worker.exe' }
foreach($name in $runtimeFiles) { Add-File (Join-Path $modSource $name) ('ModCarrerMode\'+$name) }
foreach($folder in @('config','data','mods','assets')) {
    $base=Join-Path $modSource $folder
    if (-not (Test-Path -LiteralPath $base)) { continue }
    foreach($file in Get-ChildItem -LiteralPath $base -Recurse -File) {
        if ($file.Extension -in @('.md','.ps1','.example')) { continue }
        $relative='ModCarrerMode\'+$folder+'\'+$file.FullName.Substring($base.Length+1)
        Add-File $file.FullName $relative
    }
}
$dataSource=Join-Path $repoSource 'data'
foreach($file in Get-ChildItem -LiteralPath $dataSource -Recurse -File) { Add-File $file.FullName ('data\'+$file.FullName.Substring($dataSource.Length+1)) }
$birthdateSource = Join-Path $modSource 'mods\career_birthdate_2006\payload\vpro_proinfo.big'
$birthdateRelative = 'data\ui\game\screens\virtualpro\vpro_proinfo.big'
$birthdateTarget = Join-Path $game $birthdateRelative
$stockBirthdateHash = '9AD35D2B5932D4F454012E5BEF63683C49BEBA2225BACC3FC5439D96D518FAC9'
$patchedBirthdateHash = 'B5CFF1DF25EAFE1453E11589CFD39675463DB3A63F80371C967CB47F88B342CE'
if ((Get-Sha256 $birthdateSource) -ne $patchedBirthdateHash) { throw 'Payload de nascimento diferente do build validado.' }
if (Test-Path -LiteralPath $birthdateTarget -PathType Leaf) {
    $currentHash = Get-Sha256 $birthdateTarget
    if ($currentHash -ne $stockBirthdateHash -and $currentHash -ne $patchedBirthdateHash) { throw 'Interface de nascimento desconhecida; preserve essa variante antes de instalar.' }
}
Add-File $birthdateSource $birthdateRelative
$skip=[Collections.Generic.List[object]]::new();$changes=[Collections.Generic.List[object]]::new();$same=0
foreach($file in $files) {
    $exists=Test-Path -LiteralPath $file.Target -PathType Leaf
    $legacyConfig=$null
    $editionOwnedConfig = $file.Relative -in @('ModCarrerMode\config\edition.ini','ModCarrerMode\config\career_retirement_background.ini')
    if ($file.Relative.StartsWith('ModCarrerMode\config\')) { $legacyConfig=Join-Path $gameMod ([IO.Path]::GetFileName($file.Target)) }
    if (((($file.Relative.StartsWith('ModCarrerMode\config\') -or $file.Relative -eq 'ModCarrerMode\crowd.ini') -and -not $editionOwnedConfig -and -not $ReplaceConfiguration -and ($exists -or ($legacyConfig -and (Test-Path -LiteralPath $legacyConfig)))) -or
         ($file.Relative.EndsWith('.db') -and $exists -and -not $RestoreLocalization))) {
        $skip.Add($file);continue
    }
    if ($exists -and (Get-Sha256 $file.Target) -eq $file.Hash) { $same++;continue }
    $changes.Add($file)
}
$obsoletePaths = @('dinput8_career_chain.dll','ModCarrerMode\mods\bench12_global_limit_12_v2')
if ($edition -eq 'v12') {
    $obsoletePaths += @('ModCarrerMode\assets','ModCarrerMode\career_operations_worker.exe','ModCarrerMode\config\ranking_overlay.ini','ModCarrerMode\ranking_overlay.ini')
}
$obsoletePaths = @($obsoletePaths | Where-Object { Test-Path -LiteralPath (Join-Path $game $_) })
if ($VerifyOnly) {
    [pscustomobject]@{Edition=$edition;DevFiles=$files.Count;Identical=$same;Preserved=$skip.Count;ToInstall=$changes.Count;ToArchive=$obsoletePaths.Count}
    $changes | Select-Object Relative
    $obsoletePaths | ForEach-Object { [pscustomobject]@{Archive=$_} }
    return
}
if (Get-Process FIFA16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA antes de instalar. Os arquivos Dev ja estao prontos.' }
if (($changes | Where-Object { $_.Relative -eq 'Server16Python.exe' }) -and (Get-Process Server16Python -ErrorAction SilentlyContinue)) { throw 'Feche o Server16Python antes de atualizar seu executavel.' }
$backup=Join-Path ([IO.Path]::GetFullPath($BackupDirectory)) ('ModCarrerMode_install_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null
function Backup-File([string]$Target,[string]$Relative) {
    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) { return }
    $dest=Join-Path $backup $Relative;Assert-Child $backup $dest
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dest)) | Out-Null
    Copy-Item -LiteralPath $Target -Destination $dest
    if ((Get-Sha256 $Target) -ne (Get-Sha256 $dest)) { throw "Falha no backup: $Relative" }
}
# Copy and verify every overwritten file BEFORE modifying the installation.
foreach($file in $changes) { Backup-File $file.Target $file.Relative }
foreach($relative in $obsoletePaths) {
    $old=Join-Path $game $relative
    $dest=Join-Path $backup ('edition-switch\'+$relative)
    Assert-Child $game $old;Assert-Child $backup $dest
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dest)) | Out-Null
    Move-Item -LiteralPath $old -Destination $dest
}
New-Item -ItemType Directory -Force -Path $gameMod | Out-Null
foreach($folder in @('config','data\catalogs','logs','runtime')) { New-Item -ItemType Directory -Force -Path (Join-Path $gameMod $folder) | Out-Null }
$moves=Get-Content -LiteralPath (Join-Path $modSource 'docs\runtime-migration-20261003.json') -Raw | ConvertFrom-Json
foreach($item in $moves.PSObject.Properties) {
    $old=Join-Path $gameMod $item.Name;$new=Join-Path $gameMod $item.Value
    if (-not (Test-Path -LiteralPath $old -PathType Leaf)) { continue }
    Assert-Child $gameMod $old;Assert-Child $gameMod $new
    Backup-File $old ('legacy\'+$item.Name)
    if (Test-Path -LiteralPath $new) {
        $archive=Join-Path $backup ('legacy-duplicates\'+$item.Name)
        Assert-Child $backup $archive
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($archive)) | Out-Null
        Move-Item -LiteralPath $old -Destination $archive
    } else { Move-Item -LiteralPath $old -Destination $new }
}
# Existing diagnostics are archived into logs, not discarded.
foreach($log in Get-ChildItem -LiteralPath $gameMod -File -Filter '*.log') {
    $target=Join-Path $gameMod ('logs\'+$log.Name);Assert-Child $gameMod $log.FullName;Assert-Child $gameMod $target
    if (Test-Path -LiteralPath $target) { $target=Join-Path $gameMod ('logs\'+$log.BaseName+'_before_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'.log') }
    Move-Item -LiteralPath $log.FullName -Destination $target
}
foreach($file in $changes) {
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($file.Target)) | Out-Null
    Copy-Item -LiteralPath $file.Source -Destination $file.Target -Force
    if ((Get-Sha256 $file.Target) -ne $file.Hash) { throw "Copia divergente: $($file.Relative). Backup: $backup" }
}
if ($ArchiveDevelopmentFiles) {
    foreach($folder in @('source','tools','backups')) {
        $old=Join-Path $gameMod $folder
        if (-not (Test-Path -LiteralPath $old -PathType Container)) { continue }
        $dest=Join-Path $backup ('development-files\'+$folder)
        Assert-Child $gameMod $old;Assert-Child $backup $dest
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dest)) | Out-Null
        Move-Item -LiteralPath $old -Destination $dest
    }
}
[pscustomobject]@{Edition=$edition;Installed=$changes.Count;Identical=$same;Preserved=$skip.Count;Archived=$obsoletePaths.Count;Backup=$backup;Game=$game}
