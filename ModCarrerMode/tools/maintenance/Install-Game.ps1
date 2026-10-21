[CmdletBinding()]
param(
    [string]$GameDirectory = 'U:\fifa 16',
    [string]$BackupDirectory = 'J:\mods\backup',
    [switch]$RestoreLocalization,
    [switch]$ReplaceDatabase,
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
& (Join-Path $PSScriptRoot 'Verify-Package.ps1') -PackageRoot $repoSource | Out-Null
$game = (Resolve-Path -LiteralPath $GameDirectory).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $game 'FIFA16.exe'))) { throw 'A pasta selecionada nao contem FIFA16.exe.' }
if ($game -eq $repoSource) { throw 'O destino nao pode ser a pasta Dev.' }
$gameMod = Join-Path $game 'ModCarrerMode'
# Live integration keeps DB/localization/DLC owned by their external package.
# An ordinary mod update must never write the repository's older data through
# these junctions or archive files inside the live development modules.
$externalPaths = @()
foreach ($relative in @('data\db','data\loc','dlc')) {
    $item = Get-Item -LiteralPath (Join-Path $game $relative) -Force -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType) { $externalPaths += $relative }
}
$modsItem = Get-Item -LiteralPath (Join-Path $gameMod 'mods') -Force -ErrorAction SilentlyContinue
$liveMods = $modsItem -and $modsItem.LinkType
$enabledPlugins=@(Get-Content -LiteralPath (Join-Path $modSource 'mods\enabled.txt') | ForEach-Object { $_.Trim() })
if ($enabledPlugins -contains 'subson\subson_bridge.dll') {
    $subsonAsset=Get-Content -LiteralPath (Join-Path $modSource 'data\catalogs\subson_assets.json') -Raw | ConvertFrom-Json
    $payload=$subsonAsset.files[0]
    $installedPayload=Join-Path $game 'data\ant.cbac'
    if (-not (Test-Path -LiteralPath $installedPayload -PathType Leaf) -or
        (Get-Item -LiteralPath $installedPayload).Length -ne $payload.bytes -or
        (Get-Sha256 $installedPayload) -ne ([string]$payload.sha256).ToUpperInvariant()) {
        throw "Instale primeiro o complemento $($subsonAsset.archive) na pasta do jogo. O arquivo data\ant.cbac necessario ao SubsOn esta ausente ou diferente."
    }
}
$missingVarAssets=@()
if ($enabledPlugins -contains 'var_cabin\var_cabin.dll') {
    foreach ($relative in @('data\sceneassets\var_cabin\model.rx3','data\sceneassets\var_cabin\textures.rx3')) {
        if (-not (Test-Path -LiteralPath (Join-Path $game $relative) -PathType Leaf)) {
            $missingVarAssets+=$relative
        }
    }
}
if ($missingVarAssets.Count) {
    if ($liveMods) { Write-Warning 'Cabine do VAR sem assets locais: os outros mods serao instalados; a lista compartilhada do desenvolvimento sera preservada.' }
    else { Write-Warning 'Cabine do VAR sem assets locais: os outros mods serao instalados. A cabine sera desabilitada nesta instalacao; instale seus assets e reinstale para habilitar.' }
}
if ($enabledPlugins -contains 'smoke_machine\smoke_machine.dll') {
    foreach ($relative in @('data\sceneassets\smoke_machine\model.rx3','data\sceneassets\smoke_machine\textures.rx3')) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoSource $relative) -PathType Leaf)) {
            throw "A máquina de fumaça precisa do asset no pacote: $relative."
        }
    }
}
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
    if ($Relative -eq 'ModCarrerMode\mods\enabled.txt' -and $missingVarAssets.Count -and -not $liveMods) {
        # Destination-specific optional module gate; never rewrite the development list.
        $text=[IO.File]::ReadAllText($Source)
        $text=[regex]::Replace($text,'(?m)^[ \t]*var_cabin\\var_cabin\.dll[ \t]*\r?\n?','')
        $content=[Text.UTF8Encoding]::new($false).GetBytes($text)
        $sha=[Security.Cryptography.SHA256]::Create()
        try { $hash=[BitConverter]::ToString($sha.ComputeHash($content)).Replace('-','') } finally { $sha.Dispose() }
        $files.Add([pscustomobject]@{Source=$Source;Relative=$Relative;Target=$target;Hash=$hash;Content=$content})
        return
    }
    $files.Add([pscustomobject]@{Source=$Source;Relative=$Relative;Target=$target;Hash=(Get-Sha256 $Source)})
}
foreach($name in @('dinput8.dll','dinput8_orig.dll','dinput8_L9.ini','dinput8_patch.ini','winmm.dll','Server16Python.exe')) { Add-File (Join-Path $repoSource $name) $name }
# SubsOn root payload: the original dinput8 chain remains authoritative.
if ($enabledPlugins -contains 'subson\subson_bridge.dll') {
    foreach ($name in @('SubsOn.dll','SubsOn.ini')) { Add-File (Join-Path $repoSource $name) $name }
}
$swissMemorySource = Join-Path $modSource 'assets\swiss\memoryfw.ini'
if (Test-Path -LiteralPath $swissMemorySource -PathType Leaf) { Add-File $swissMemorySource 'memoryfw.ini' }
$runtimeFiles = @('retirement_offline_worker.exe','crowd.ini')
if ($edition -eq 'new-experience') { $runtimeFiles += 'career_operations_worker.exe' }
foreach($name in $runtimeFiles) { Add-File (Join-Path $modSource $name) ('ModCarrerMode\'+$name) }
if (@($enabledPlugins | Where-Object { $_ -match '^frontend_stadium[\\/]' }).Count) {
    Add-File (Join-Path $modSource 'tools\frontend_stadium_prepare.exe') 'ModCarrerMode\tools\frontend_stadium_prepare.exe'
}
foreach($folder in @('config','data','mods','assets')) {
    $base=Join-Path $modSource $folder
    if (-not (Test-Path -LiteralPath $base)) { continue }
    foreach($file in Get-ChildItem -LiteralPath $base -Recurse -File) {
        # This payload belongs at the game root; do not recreate a legacy
        # ModCarrerMode/assets tree that V12 archives on every installation.
        if ($file.FullName -eq $swissMemorySource) { continue }
        if ($folder -eq 'mods' -and $file.FullName -match '[\\/]skip_server_shutdown_notice[\\/]') { continue }
        if ($folder -eq 'mods' -and $file.Name -eq 'runtime_state.txt') { continue }
        if ($file.Name -like '*.in_use_backup_*') { continue }
        if ($file.Name -like '*.before-*') { continue }
        if ($folder -eq 'mods' -and ($file.FullName -match '[\\/]source[\\/]' -or $file.Extension -in @('.cpp','.c','.h','.cmd','.json','.log','.tmp'))) { continue }
        if ($file.Extension -in @('.md','.ps1','.example','.bak')) { continue }
        $relative='ModCarrerMode\'+$folder+'\'+$file.FullName.Substring($base.Length+1)
        Add-File $file.FullName $relative
    }
}
$dataSource=Join-Path $repoSource 'data'
$localCalendarIcons=(Join-Path $dataSource 'ui\imgAssets\careerCompetitionIcons').TrimEnd('\')+'\'
foreach($file in Get-ChildItem -LiteralPath $dataSource -Recurse -File) {
    $relativeData = 'data\'+$file.FullName.Substring($dataSource.Length+1)
    if (@($externalPaths | Where-Object { $relativeData.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase) }).Count) { continue }
    # Calendar images/index are local resources; update only the lookup module.
    if ($file.FullName.StartsWith($localCalendarIcons,[StringComparison]::OrdinalIgnoreCase)) { continue }
    if ($file.FullName -match '[\\/]sceneassets[\\/](entrance_props|var_cabin)[\\/]') { continue }
    if ($file.FullName -match '[\\/]entrance_props[\\/].*[\\/]fixtures[\\/]') { continue }
    if ($file.Extension -eq '.md' -or ($file.FullName -match '[\\/]entrance_props[\\/]' -and $file.Extension -in @('.png','.jpg','.html','.json'))) { continue }
    Add-File $file.FullName ('data\'+$file.FullName.Substring($dataSource.Length+1))
}
# Competition rules belong to this exact DLC path. Only source payload files
# are installed; schedules and other existing DLC files remain game-owned.
$compdataRelative = 'dlc\dlc_FootballCompEng\dlc\FootballCompEng\data\compdata'
$compdataSource = Join-Path $repoSource $compdataRelative
if (($externalPaths -notcontains 'dlc') -and (Test-Path -LiteralPath $compdataSource -PathType Container)) {
    foreach($file in Get-ChildItem -LiteralPath $compdataSource -File -Filter '*.txt') {
        Add-File $file.FullName ($compdataRelative+'\'+$file.Name)
    }
}
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
    $careerDatabase = $file.Relative -in @('data\db\fifa_ng_db.db','data\db\fifa_ng_db-meta.xml')
    # Keep DB and metadata together. Replacing a career DB is an explicit
    # installation choice, separate from restoring interface localization.
    if ($careerDatabase -and -not $ReplaceDatabase -and (Test-Path -LiteralPath (Join-Path $game 'data\db\fifa_ng_db.db'))) {
        $skip.Add($file);continue
    }
    if ($file.Relative.StartsWith('ModCarrerMode\config\')) { $legacyConfig=Join-Path $gameMod ([IO.Path]::GetFileName($file.Target)) }
    if (((($file.Relative.StartsWith('ModCarrerMode\config\') -or $file.Relative -eq 'ModCarrerMode\crowd.ini') -and -not $editionOwnedConfig -and -not $ReplaceConfiguration -and ($exists -or ($legacyConfig -and (Test-Path -LiteralPath $legacyConfig)))) -or
         ($file.Relative.EndsWith('.db') -and $exists -and -not $RestoreLocalization -and -not ($careerDatabase -and $ReplaceDatabase)))) {
        $skip.Add($file);continue
    }
    if ($exists -and (Get-Sha256 $file.Target) -eq $file.Hash) { $same++;continue }
    $changes.Add($file)
}
$obsoletePaths = @('dinput8_career_chain.dll','ModCarrerMode\mods\bench12_global_limit_12_v2',
    'ModCarrerMode\config\entrance_competitions.ini','ModCarrerMode\entrance_competitions.ini')
if ($enabledPlugins -contains 'subson\subson_bridge.dll') { $obsoletePaths += 'ModCarrerMode\mods\bench_native12' }
if (-not $liveMods) {
    $obsoletePaths += 'ModCarrerMode\mods\skip_server_shutdown_notice'
    if (-not @($enabledPlugins | Where-Object { $_ -match '^extra_scenes[\\/]' }).Count) {
        $obsoletePaths += 'ModCarrerMode\mods\extra_scenes'
    }
}
# Upgrade old packages to one DLL per mod. Archive only known module folders;
# unrelated user-installed modules remain outside this migration.
$installedMods = Join-Path $gameMod 'mods'
$packageMods = Join-Path $modSource 'mods'
if (-not $liveMods -and (Test-Path -LiteralPath $installedMods -PathType Container)) {
    foreach ($directory in Get-ChildItem -LiteralPath $installedMods -Directory) {
        if ($directory.Name -match '^kickoff_modern(?:_restore)?_v\d+$') {
            $obsoletePaths += 'ModCarrerMode\mods\'+$directory.Name
        }
    }
    foreach ($directory in Get-ChildItem -LiteralPath $packageMods -Directory) {
        $installedModule = Join-Path $installedMods $directory.Name
        if (-not (Test-Path -LiteralPath $installedModule -PathType Container)) { continue }
        foreach ($oldFile in Get-ChildItem -LiteralPath $installedModule -Recurse -File) {
            $isBackup=$oldFile.Name -like '*.before-*' -or $oldFile.Name -like '*.in_use_backup_*'
            if ($oldFile.Extension -ne '.dll' -and $oldFile.Name -notlike '*animation_command*.txt' -and -not $isBackup) { continue }
            $moduleRelative = $oldFile.FullName.Substring($installedMods.Length+1)
            if (-not (Test-Path -LiteralPath (Join-Path $packageMods $moduleRelative) -PathType Leaf)) {
                $obsoletePaths += 'ModCarrerMode\mods\'+$moduleRelative
            }
        }
    }
    foreach ($oldFile in Get-ChildItem -LiteralPath $installedMods -File) {
        if ($oldFile.Extension -eq '.bak' -or $oldFile.Name -eq 'enabled_birthdate_2006.txt') {
            $obsoletePaths += 'ModCarrerMode\mods\'+$oldFile.Name
        }
    }
}
if ($edition -eq 'v12') {
    if (-not $liveMods) { $obsoletePaths += 'ModCarrerMode\assets' }
    $obsoletePaths += @('ModCarrerMode\career_operations_worker.exe','ModCarrerMode\config\ranking_overlay.ini','ModCarrerMode\ranking_overlay.ini')
}
$obsoletePaths = @($obsoletePaths | Select-Object -Unique | Where-Object { Test-Path -LiteralPath (Join-Path $game $_) })
# A directory already carries its children into the backup. Do not move a child
# a second time after its parent has been archived.
$archiveRoots = @()
foreach ($relative in @($obsoletePaths | Sort-Object Length)) {
    if (-not @($archiveRoots | Where-Object { $relative.StartsWith($_.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase) }).Count) {
        $archiveRoots += $relative
    }
}
$obsoletePaths = $archiveRoots
if ($VerifyOnly) {
    [pscustomobject]@{Edition=$edition;DevFiles=$files.Count;Identical=$same;Preserved=$skip.Count;ToInstall=$changes.Count;ToArchive=$obsoletePaths.Count;ExternalPaths=$externalPaths;LiveDevelopmentMods=[bool]$liveMods}
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
$installationPlan = foreach($file in $changes) {
    $saved = Join-Path $backup $file.Relative
    [pscustomobject]@{
        Relative=$file.Relative
        ExistedBefore=(Test-Path -LiteralPath $saved -PathType Leaf)
        BeforeHash=$(if (Test-Path -LiteralPath $saved -PathType Leaf) { Get-Sha256 $saved } else { $null })
        AfterHash=$file.Hash
    }
}
ConvertTo-Json -InputObject @($installationPlan) -Depth 4 | Set-Content -LiteralPath (Join-Path $backup 'installation-plan.json') -Encoding utf8
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
    if ($null -ne $file.Content) { [IO.File]::WriteAllBytes($file.Target,$file.Content) }
    else { Copy-Item -LiteralPath $file.Source -Destination $file.Target -Force }
    if ((Get-Sha256 $file.Target) -ne $file.Hash) { throw "Copia divergente: $($file.Relative). Backup: $backup" }
}
if ($ArchiveDevelopmentFiles) {
    # tools contains the runtime stadium preparer, required after installation.
    foreach($folder in @('source','backups')) {
        $old=Join-Path $gameMod $folder
        if (-not (Test-Path -LiteralPath $old -PathType Container)) { continue }
        $dest=Join-Path $backup ('development-files\'+$folder)
        Assert-Child $gameMod $old;Assert-Child $backup $dest
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dest)) | Out-Null
        Move-Item -LiteralPath $old -Destination $dest
    }
}
[pscustomobject]@{Edition=$edition;Installed=$changes.Count;Identical=$same;Preserved=$skip.Count;Archived=$obsoletePaths.Count;Backup=$backup;Game=$game}
