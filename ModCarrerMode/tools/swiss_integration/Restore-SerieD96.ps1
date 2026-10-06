[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BackupDirectory,
    [string]$GameDirectory='U:\fifa 16',
    [string]$DevDirectory='J:\mods\fifa 16\fifa-mods-dev\fifa-mods-dev',
    [ValidateSet('Both','Game','Dev')][string]$Scope='Both'
)
$ErrorActionPreference='Stop'
$backup=(Resolve-Path -LiteralPath $BackupDirectory).Path.TrimEnd('\')
function Child([string]$base,[string]$relative) {
    $full=[IO.Path]::GetFullPath((Join-Path $base $relative))
    if (-not $full.StartsWith($base.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Caminho fora da pasta: $relative" }
    return $full
}
function Hash([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
if (Get-Process FIFA16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA antes de restaurar.' }
$jobs=[Collections.Generic.List[object]]::new()
if ($Scope -in @('Both','Game')) {
    $game=(Resolve-Path -LiteralPath $GameDirectory).Path.TrimEnd('\')
    if (-not (Test-Path -LiteralPath (Child $game 'FIFA16.exe') -PathType Leaf)) { throw 'Pasta do jogo invalida.' }
    $install=(Get-Content -LiteralPath (Child $backup 'game-installation-backup.txt') -Raw).Trim()
    $install=(Resolve-Path -LiteralPath $install).Path.TrimEnd('\')
    if (-not $install.StartsWith($backup+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Instalacao fora do backup.' }
    foreach($item in @(Get-Content -LiteralPath (Child $install 'installation-plan.json') -Raw | ConvertFrom-Json)) {
        $jobs.Add([pscustomobject]@{Scope='game';Target=(Child $game $item.Relative);Saved=(Child $install $item.Relative);Relative=$item.Relative;Before=$item.BeforeHash;After=$item.AfterHash;Existed=$item.ExistedBefore})
    }
}
if ($Scope -in @('Both','Dev')) {
    $dev=(Resolve-Path -LiteralPath $DevDirectory).Path.TrimEnd('\')
    $branch=& git -C $dev branch --show-current
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'fifa-friends-v12-integracao-suico') { throw 'A restauracao Dev exige a branch de integracao; a V12 nao sera alterada.' }
    foreach($item in @(Get-Content -LiteralPath (Child $backup 'dev-installation-plan.json') -Raw | ConvertFrom-Json)) {
        $jobs.Add([pscustomobject]@{Scope='dev';Target=(Child $dev $item.relative);Saved=(Child $backup ('dev-files-before\'+$item.relative));Relative=$item.relative;Before=$item.before_hash;After=$item.after_hash;Existed=$item.existed})
    }
}
# Validate ALL inputs before replacing any file. Later user changes are never
# overwritten silently. Leaf moves are confined to the requested roots.
foreach($job in $jobs) {
    if ($job.Existed -and (-not (Test-Path -LiteralPath $job.Saved -PathType Leaf) -or (Hash $job.Saved) -ne $job.Before)) { throw "Backup divergente: $($job.Relative)" }
    if ((Test-Path -LiteralPath $job.Target -PathType Leaf) -and (Hash $job.Target) -ne $job.Before -and (Hash $job.Target) -ne $job.After) { throw "Arquivo modificado depois da correcao: $($job.Scope)/$($job.Relative). Preserve essa alteracao antes de restaurar." }
}
$archive=Child $backup ('correcao-retirada_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
foreach($job in $jobs) {
    $savedCurrent=Child $archive ($job.Scope+'\'+$job.Relative)
    if (Test-Path -LiteralPath $job.Target -PathType Leaf) {
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($savedCurrent)) | Out-Null
        Move-Item -LiteralPath $job.Target -Destination $savedCurrent
    }
    if ($job.Existed) {
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($job.Target)) | Out-Null
        Copy-Item -LiteralPath $job.Saved -Destination $job.Target
        if ((Hash $job.Target) -ne $job.Before) { throw "Restauracao divergente: $($job.Relative)" }
    }
}
[pscustomobject]@{Restored=$jobs.Count;Scope=$Scope;ArchivedCorrection=$archive}
