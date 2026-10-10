param([string]$GameRoot = 'U:\fifa 16', [switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
$running = Get-Process FIFA16 -ErrorAction SilentlyContinue
if (-not $VerifyOnly -and $running -and @($running.Modules | Where-Object ModuleName -match '^mascot_.*\.dll$').Count) {
    throw 'A DLL corner já está carregada; feche o FIFA antes de substituir essa versão.'
}
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$game = (Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $game 'FIFA16.exe'))) { throw 'Destino sem FIFA16.exe.' }
if ($game -eq $repo) { throw 'Destino deve ser o jogo, não a cópia de desenvolvimento.' }
$luaRelative = 'data\fifarna\lua\assets\sle.lua'
$dllRelative = 'ModCarrerMode\mods\mascot_single\mascot_goal_line.dll'
$enabledRelative = 'ModCarrerMode\mods\enabled.txt'
$luaSource = Join-Path $repo $luaRelative
$dllSource = Join-Path $repo $dllRelative
$luaTarget = Join-Path $game $luaRelative
$dllTarget = Join-Path $game $dllRelative
$enabledTarget = Join-Path $game $enabledRelative
$statePath = Join-Path $PSScriptRoot 'last_install.json'
$original = Join-Path $PSScriptRoot 'sle.lua.base-original'
foreach ($file in @($luaSource,$dllSource,$luaTarget,$enabledTarget,$original)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Arquivo ausente: $file" }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne '9AEF08F0ABEA7FF9CEF0DFF8313553A79B3783D5F15A7E5DA8278F3E0D840376') { throw 'Base original divergente.' }
$allowed = @((Get-FileHash -LiteralPath $original).Hash,(Get-FileHash -LiteralPath $luaSource).Hash)
if (Test-Path -LiteralPath $statePath) {
    $previous = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $allowed += $previous.installedLuaHash
}
if ((Get-FileHash -LiteralPath $luaTarget).Hash -notin $allowed) { throw 'O Lua do jogo recebeu outra alteração; instalação interrompida para preservá-la.' }
$assetFiles = @()
# Optional packages discovered by numeric club ID.
$assetRoot = Join-Path $repo 'data\sceneassets\mascot'
foreach ($directory in @(Get-ChildItem -LiteralPath $assetRoot -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d+$' })) {
    $club = $directory.Name
    if (-not (Test-Path -LiteralPath (Join-Path $directory.FullName 'model.rx3')) -or -not (Test-Path -LiteralPath (Join-Path $directory.FullName 'textures.rx3'))) { Write-Warning "Pacote incompleto ignorado: $club"; continue }
    foreach ($name in @('model.rx3','textures.rx3','model_animated.rx3')) {
        $relative = "data\sceneassets\mascot\$club\$name"
        $source = Join-Path $repo $relative
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { continue }
        $assetFiles += [pscustomobject]@{Source=$source;Target=(Join-Path $game $relative);Relative=$relative}
    }
}
if ($VerifyOnly) {
    foreach ($pair in @(@($luaSource,$luaTarget),@($dllSource,$dllTarget))) {
        if (-not (Test-Path -LiteralPath $pair[1]) -or (Get-FileHash -LiteralPath $pair[0]).Hash -ne (Get-FileHash -LiteralPath $pair[1]).Hash) { throw "Instalacao divergente: $($pair[1])" }
    }
    foreach ($asset in $assetFiles) {
        if (-not (Test-Path -LiteralPath $asset.Target) -or (Get-FileHash -LiteralPath $asset.Source).Hash -ne (Get-FileHash -LiteralPath $asset.Target).Hash) { throw "Asset divergente: $($asset.Target)" }
    }
    $entries = @([IO.File]::ReadAllLines($enabledTarget) | Where-Object { $_.Trim() -match '^mascot_single\\.*\.dll$' })
    if ($entries.Count -ne 1 -or $entries[0].Trim() -ne 'mascot_single\mascot_goal_line.dll') { throw 'Registro do plugin divergente.' }
    [pscustomobject]@{Game=$game;Version=13;Verified=$true;Assets=$assetFiles.Count;AutomaticPlugin=$entries[0].Trim()}
    return
}
$backupRelative = 'backups\'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')
$backup = Join-Path $PSScriptRoot $backupRelative
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath $luaTarget -Destination (Join-Path $backup 'sle.lua.before')
Copy-Item -LiteralPath $enabledTarget -Destination (Join-Path $backup 'enabled.txt.before')
if (Test-Path -LiteralPath $dllTarget) { Copy-Item -LiteralPath $dllTarget -Destination (Join-Path $backup 'mascot_single.dll.before') }
if ($previous -and $previous.pluginEntry) {
    $previousDll = Join-Path (Join-Path $game 'ModCarrerMode\mods') $previous.pluginEntry
    if (Test-Path -LiteralPath $previousDll) { Copy-Item -LiteralPath $previousDll -Destination (Join-Path $backup 'previous_plugin.dll') }
}
if (Test-Path -LiteralPath $statePath) { Copy-Item -LiteralPath $statePath -Destination (Join-Path $backup 'last_install.before.json') }
New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dllTarget)) | Out-Null
foreach ($asset in $assetFiles) {
    if (Test-Path -LiteralPath $asset.Target -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $asset.Source).Hash -eq (Get-FileHash -LiteralPath $asset.Target).Hash) { continue }
        $saved = Join-Path $backup $asset.Relative
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($saved)) | Out-Null
        Copy-Item -LiteralPath $asset.Target -Destination $saved
    }
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($asset.Target)) | Out-Null
    Copy-Item -LiteralPath $asset.Source -Destination $asset.Target -Force
    if ((Get-FileHash -LiteralPath $asset.Source).Hash -ne (Get-FileHash -LiteralPath $asset.Target).Hash) { throw 'Falha ao copiar o pacote de mascote.' }
}
Copy-Item -LiteralPath $dllSource -Destination $dllTarget -Force
Copy-Item -LiteralPath $luaSource -Destination $luaTarget -Force
$entry = 'mascot_single\mascot_goal_line.dll'
$enabled = [IO.File]::ReadAllText($enabledTarget)
$enabled = (($enabled -split '\r?\n') | Where-Object { $_.Trim() -notmatch '^mascot_single\\.*\.dll$' }) -join "`r`n"
$enabled = $enabled.Replace('# Mascote em uma única instância de fotógrafo.','# Mascote: uma posição perto de uma esquina do campo.').Replace('# Mascote: diagnóstico nos fotógrafos de número par.','# Mascote: uma posição perto de uma esquina do campo.')
if ($entry -notin @($enabled -split '\r?\n' | ForEach-Object { $_.Trim() })) {
    [IO.File]::WriteAllText($enabledTarget,$enabled.TrimEnd()+"`r`n"+$entry+"`r`n",[Text.UTF8Encoding]::new($false))
} else {
    [IO.File]::WriteAllText($enabledTarget,$enabled,[Text.UTF8Encoding]::new($false))
}
foreach ($pair in @(@($luaSource,$luaTarget),@($dllSource,$dllTarget))) {
    if ((Get-FileHash -LiteralPath $pair[0]).Hash -ne (Get-FileHash -LiteralPath $pair[1]).Hash) { throw 'Falha de cópia; consulte o backup.' }
}
$state = [ordered]@{
    version = 13
    selectionMode = 'one_near_goal_line_corner'
    gameRoot = $game
    installedAt = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    backupRelativePath = $backupRelative
    restoreOriginalPath = 'sle.lua.base-original'
    originalLuaHash = (Get-FileHash -LiteralPath $original).Hash
    installedLuaHash = (Get-FileHash -LiteralPath $luaTarget).Hash
    installedDllHash = (Get-FileHash -LiteralPath $dllTarget).Hash
    pluginEntry = $entry
    assetFilesVerified = $assetFiles.Count
    gameplayValidation = 'pending'
    gameWasRunningAtInstall = [bool]$running
}
$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
[pscustomobject]@{Game=$game;Version=13;Mode='one_near_goal_line_corner';Lua=$state.installedLuaHash;Dll=$state.installedDllHash;Backup=$backup;RequiresReload=[bool]$running}
