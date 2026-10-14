[CmdletBinding()]
param(
    [string]$GameDirectory = 'U:\fifa 16',
    [Parameter(Mandatory=$true)][string]$DatabasePackage,
    [string]$BackupDirectory = 'U:\mods\backup',
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$dev = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..')).TrimEnd('\')
$game = (Resolve-Path -LiteralPath $GameDirectory).Path.TrimEnd('\')
$package = (Resolve-Path -LiteralPath $DatabasePackage).Path.TrimEnd('\')
if ($game -eq $dev -or $game -eq $package) { throw 'O jogo, o desenvolvimento e o pacote precisam de pastas distintas.' }
function Assert-Child([string]$Base, [string]$Path) {
    $baseFull = [IO.Path]::GetFullPath($Base).TrimEnd('\') + '\'
    if (-not [IO.Path]::GetFullPath($Path).StartsWith($baseFull, [StringComparison]::OrdinalIgnoreCase)) { throw "Caminho fora da pasta autorizada: $Path" }
}
function Hash([string]$Path) { if (Test-Path -LiteralPath $Path -PathType Leaf) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash } else { $null } }
& (Join-Path $PSScriptRoot 'Verify-Package.ps1') -PackageRoot $dev | Out-Null
foreach ($relative in @('fifa16.exe', 'data\sceneassets\var_cabin\model_v2.rx3', 'data\sceneassets\var_cabin\textures_v2.rx3')) {
    if (-not (Test-Path -LiteralPath (Join-Path $game $relative) -PathType Leaf)) { throw "Arquivo necessario no jogo: $relative" }
}
foreach ($relative in @('data\db\fifa_ng_db.db','data\db\fifa_ng_db-meta.xml','data\loc\por_br.db','dlc\dlc_FootballCompEng\dlc\FootballCompEng\data\compdata\settings.txt')) {
    if (-not (Test-Path -LiteralPath (Join-Path $package $relative) -PathType Leaf)) { throw "Pacote incompleto: $relative" }
}
if ((Hash (Join-Path $dev 'data\db\fifa_ng_db-meta.xml')) -ne (Hash (Join-Path $package 'data\db\fifa_ng_db-meta.xml'))) { throw 'Os metadados do novo DB precisam de uma analise de compatibilidade.' }
$links = @(
    [pscustomobject]@{Relative='data\db'; Source=(Join-Path $package 'data\db')},
    [pscustomobject]@{Relative='data\loc'; Source=(Join-Path $package 'data\loc')},
    [pscustomobject]@{Relative='dlc'; Source=(Join-Path $package 'dlc')},
    [pscustomobject]@{Relative='ModCarrerMode\mods'; Source=(Join-Path $dev 'ModCarrerMode\mods')}
)
foreach ($link in $links) {
    $target = Join-Path $game $link.Relative
    Assert-Child $game $target
    if (-not (Test-Path -LiteralPath $link.Source -PathType Container)) { throw "Origem ausente: $($link.Source)" }
    $item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
    $already = $item -and $item.LinkType -eq 'Junction' -and [IO.Path]::GetFullPath([string]@($item.Target)[0]).TrimEnd('\') -eq $link.Source
    if ($item -and $item.LinkType -and -not $already) { throw "Link existente aponta para outra origem: $target" }
    $link | Add-Member NoteProperty Connected ([bool]$already)
}
$files = [Collections.Generic.List[object]]::new()
function Add-File([string]$Source, [string]$Relative) {
    $target = Join-Path $game $Relative
    Assert-Child $game $target
    $expected = Hash $Source
    if (-not $expected) { throw "Arquivo ausente: $Source" }
    if ($expected -ne (Hash $target)) { $files.Add([pscustomobject]@{Relative=$Relative; Source=$Source; Hash=$expected; Before=(Hash $target)}) }
}
# DB, language databases and DLC use their own live directories. Existing
# mascot, animation and 3D development assets are never replaced by the pack.
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $package 'data') -Recurse -File) {
    $relative = $file.FullName.Substring($package.Length + 1)
    if ($relative -match '^data\\(db|loc)\\') { continue }
    if ($relative -match '^data\\sceneassets\\' -and $relative -notmatch '^data\\sceneassets\\(banner|flag|kit)\\') { continue }
    $developmentFile = Join-Path $dev $relative
    if (Test-Path -LiteralPath $developmentFile -PathType Leaf) { Add-File $developmentFile $relative }
    else { Add-File $file.FullName $relative }
}
foreach ($name in @('dinput8.dll','dinput8_orig.dll','dinput8_L9.ini','dinput8_patch.ini','winmm.dll','Server16Python.exe')) { Add-File (Join-Path $dev $name) $name }
foreach ($relative in @('ModCarrerMode\retirement_offline_worker.exe','memoryfw.ini')) {
    $source = Join-Path $dev $relative
    if ($relative -eq 'memoryfw.ini') { $source = Join-Path $dev 'ModCarrerMode\assets\swiss\memoryfw.ini' }
    if (Test-Path -LiteralPath $source -PathType Leaf) { Add-File $source $relative }
}
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $dev 'ModCarrerMode\data') -Recurse -File) { Add-File $file.FullName $file.FullName.Substring($dev.Length+1) }
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $dev 'ModCarrerMode\config') -File) {
    $relative = $file.FullName.Substring($dev.Length+1)
    if (-not (Test-Path -LiteralPath (Join-Path $game $relative) -PathType Leaf)) { Add-File $file.FullName $relative }
}
$plan = [pscustomobject]@{Game=$game; Development=$dev; DatabasePackage=$package; Links=$links; FilesToCopy=$files.Count; Files=$files}
if ($VerifyOnly) { return $plan }
if (Get-Process fifa16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA para conectar as pastas.' }
if (($files | Where-Object Relative -eq 'Server16Python.exe') -and (Get-Process Server16Python -ErrorAction SilentlyContinue)) { throw 'O executavel do Server16 esta em uso e precisa ser fechado para atualizar.' }
$backup = Join-Path ([IO.Path]::GetFullPath($BackupDirectory)) ('DB_DLC_Dev_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null
$plan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'plan.json') -Encoding utf8
$protected = [Collections.Generic.List[object]]::new()
foreach ($relative in @('data\sceneassets\mascot','data\sceneassets\entrance_props','data\sceneassets\var_cabin','data\sceneassets\multiball','data\sceneassets\particles','ModCarrerMode\assets')) {
    $directory = Join-Path $game $relative
    if (Test-Path -LiteralPath $directory -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $directory -Recurse -File) {
            $protected.Add([pscustomobject]@{Relative=$file.FullName.Substring($game.Length+1); Hash=(Hash $file.FullName)})
        }
    }
}
$protected | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $backup 'protected-assets.json') -Encoding utf8
# Verify all copied backups before changing any file.
foreach ($file in $files) {
    if ($file.Before) {
        $saved = Join-Path $backup ('files\'+$file.Relative)
        Assert-Child $backup $saved
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($saved)) | Out-Null
        Copy-Item -LiteralPath (Join-Path $game $file.Relative) -Destination $saved
        if ((Hash $saved) -ne $file.Before) { throw "Backup divergente: $($file.Relative)" }
    }
}
foreach ($link in $links) {
    if ($link.Connected) { continue }
    $target = Join-Path $game $link.Relative
    $saved = Join-Path $backup ('directories\'+$link.Relative)
    Assert-Child $game $target; Assert-Child $backup $saved
    if (Test-Path -LiteralPath $target) {
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($saved)) | Out-Null
        Move-Item -LiteralPath $target -Destination $saved
    }
    try { New-Item -ItemType Junction -Path $target -Target $link.Source | Out-Null }
    catch { if ((Test-Path -LiteralPath $saved) -and -not (Test-Path -LiteralPath $target)) { Move-Item -LiteralPath $saved -Destination $target }; throw }
}
foreach ($file in $files) {
    $target = Join-Path $game $file.Relative
    if ((Hash $target) -ne $file.Before) { throw "O destino mudou durante a integracao: $($file.Relative)" }
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($target)) | Out-Null
    Copy-Item -LiteralPath $file.Source -Destination $target -Force
    if ((Hash $target) -ne $file.Hash) { throw "Copia divergente: $($file.Relative)" }
}
foreach ($link in $links) {
    $item = Get-Item -LiteralPath (Join-Path $game $link.Relative) -Force
    if ($item.LinkType -ne 'Junction' -or [string]@($item.Target)[0] -ne $link.Source) { throw "Conexao divergente: $($link.Relative)" }
    $link.Connected = $true
}
foreach ($asset in $protected) { if ((Hash (Join-Path $game $asset.Relative)) -ne $asset.Hash) { throw "Asset protegido mudou: $($asset.Relative)" } }
$enabled = @(Get-Content -LiteralPath (Join-Path $game 'ModCarrerMode\mods\enabled.txt') | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
foreach ($entry in $enabled) {
    $relative = 'ModCarrerMode\mods\'+$entry.Trim()
    if ((Hash (Join-Path $game $relative)) -ne (Hash (Join-Path $dev $relative))) { throw "Mod divergente: $relative" }
}
$result = [pscustomobject]@{Game=$game; Development=$dev; DatabasePackage=$package; Backup=$backup; Copied=$files.Count; EnabledMods=$enabled.Count; ProtectedFiles=$protected.Count; Verified=$true; VerifiedInGame=$false; Links=$links}
$runtime = Join-Path $game 'runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runtime 'development-integration.json') -Encoding utf8
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backup 'result.json') -Encoding utf8
$result
