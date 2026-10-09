param([string]$GameRoot = 'U:\fifa 16')
$ErrorActionPreference = 'Stop'
if (Get-Process FIFA16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA antes de restaurar.' }
$statePath = Join-Path $PSScriptRoot 'last_install.json'
if (-not (Test-Path -LiteralPath $statePath)) { throw 'Não há registro de instalação.' }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$destination = Join-Path $GameRoot 'data\fifarna\lua\assets\sle.lua'
$currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash
if ($currentHash -ne $state.installedLuaHash) { throw 'O sle.lua do jogo mudou após a instalação; não restaurei para preservar essa alteração.' }
$backup = Join-Path $PSScriptRoot 'sle.lua.base-original'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash -ne $state.originalLuaHash) { throw 'Base de restauração divergente.' }
if ($state.version -ge 2) {
    $enabledPath = Join-Path $GameRoot 'ModCarrerMode\mods\enabled.txt'
    $lines = [IO.File]::ReadAllLines($enabledPath)
    $remaining = @($lines | Where-Object { $_.Trim() -notin @($state.pluginEntry,'mascot_single\mascot_single.dll','mascot_single\mascot_corner.dll','mascot_single\mascot_goal_line.dll','mascot_single\mascot_goal_line_v6.dll','mascot_single\mascot_goal_line_v7.dll','mascot_single\mascot_goal_line_v8.dll','mascot_single\mascot_goal_line_v9.dll','mascot_single\mascot_goal_line_v10.dll','mascot_single\mascot_goal_line_v11.dll','mascot_single\mascot_goal_line_v12.dll','mascot_single\mascot_goal_line_v13.dll') })
    [IO.File]::WriteAllLines($enabledPath,$remaining,[Text.UTF8Encoding]::new($false))
}
Copy-Item -LiteralPath $backup -Destination $destination -Force
$restoredHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash
if ($restoredHash -ne $state.originalLuaHash) { throw 'O hash restaurado não corresponde ao backup.' }
Write-Output "Lua original restaurado e plugin de mascote desativado: $destination"
