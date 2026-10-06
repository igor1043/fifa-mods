[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$InstallationBackup,
    [string]$GameDirectory='U:\fifa 16'
)
$ErrorActionPreference='Stop'
$game=(Resolve-Path -LiteralPath $GameDirectory).Path.TrimEnd('\')
$backup=(Resolve-Path -LiteralPath $InstallationBackup).Path.TrimEnd('\')
function ChildPath([string]$base,[string]$relative) {
    $result=[IO.Path]::GetFullPath((Join-Path $base $relative))
    if (-not $result.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Caminho fora da pasta: $relative" }
    return $result
}
function Hash([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
if (-not (Test-Path -LiteralPath (Join-Path $game 'FIFA16.exe') -PathType Leaf)) { throw 'Pasta do jogo invalida.' }
if (Get-Process FIFA16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA antes de restaurar.' }
$plan=@(Get-Content -LiteralPath (Join-Path $backup 'installation-plan.json') -Raw | ConvertFrom-Json)
if (-not $plan.Count) { throw 'Plano vazio.' }
$seen=@{}
foreach($item in $plan) {
    if ($seen.ContainsKey($item.Relative)) { throw 'Arquivo repetido no plano.' }
    $seen[$item.Relative]=$true
    $target=ChildPath $game $item.Relative
    $saved=ChildPath $backup $item.Relative
    if ((Test-Path -LiteralPath $target -PathType Leaf) -and (Hash $target) -ne $item.AfterHash -and (Hash $target) -ne $item.BeforeHash) { throw "Arquivo alterado depois da instalacao: $($item.Relative)" }
    if ($item.ExistedBefore -and (-not (Test-Path -LiteralPath $saved -PathType Leaf) -or (Hash $saved) -ne $item.BeforeHash)) { throw "Backup divergente: $($item.Relative)" }
}
$archive=ChildPath $backup ('revision-returned_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $archive | Out-Null
foreach($item in $plan) {
    $target=ChildPath $game $item.Relative
    $saved=ChildPath $backup $item.Relative
    $dest=ChildPath $archive $item.Relative
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dest)) | Out-Null
        Move-Item -LiteralPath $target -Destination $dest
    }
    if ($item.ExistedBefore) {
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($target)) | Out-Null
        Copy-Item -LiteralPath $saved -Destination $target
        if ((Hash $target) -ne $item.BeforeHash) { throw "Restauracao divergente: $($item.Relative)" }
    }
}
[pscustomobject]@{Restored=$plan.Count;ArchivedRevision=$archive;Game=$game}
