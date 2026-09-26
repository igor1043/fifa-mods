[CmdletBinding()]
param(
    [string]$GameRoot = 'U:\fifa 16'
)

$ErrorActionPreference = 'Stop'
$gameDll = Join-Path $GameRoot 'dinput8.dll'
$rollbackDll = Join-Path $PSScriptRoot 'rollback\dinput8.dll'

if (@(Get-Process -Name fifa16 -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Feche o FIFA 16 antes de executar o rollback.'
}
if (-not (Test-Path -LiteralPath $gameDll)) { throw "DLL ativa ausente: $gameDll" }
if (-not (Test-Path -LiteralPath $rollbackDll)) { throw "Rollback ausente: $rollbackDll" }

Copy-Item -LiteralPath $rollbackDll -Destination $gameDll -Force
Write-Output 'DLL anterior restaurada.'
