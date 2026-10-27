param([string]$GameRoot='U:\fifa 16')
$ErrorActionPreference='Stop'
if (Get-Process -Name fifa16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA antes de desinstalar. Para esconder agora, altere enabled=0 no var_cabin.ini.' }
$taskRoot=[IO.Path]::GetFullPath($GameRoot)
$targetLua=Join-Path $taskRoot 'data\fifarna\lua\assets\sle.lua'
$enabledPath=Join-Path $taskRoot 'ModCarrerMode\mods\enabled.txt'
$modulePath=Join-Path $taskRoot 'ModCarrerMode\mods\var_cabin'
$blockPath=Join-Path $modulePath 'var_cabin.lua'
$encoding=[Text.UTF8Encoding]::new($false)
$lua=[IO.File]::ReadAllText($targetLua,$encoding)
$block=[IO.File]::ReadAllText($blockPath,$encoding)
if ($lua.Contains($block)) { $newLua=$lua.Replace($block,'') } else { throw 'Bloco Lua alterado depois da instalação; preserve o arquivo e revise a remoção da seção FIFA16_VAR_CABIN_V1.' }
$enabled=[IO.File]::ReadAllText($enabledPath,$encoding)
$newEnabled=($enabled -split '\r?\n' | Where-Object { $_ -notmatch '^\s*var_cabin\\var_cabin(_v[0-9]+)?\.dll\s*$' }) -join "`r`n"
$backupPath=Join-Path $taskRoot ('ModCarrerMode\backups\var_cabin_remove_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
Copy-Item -LiteralPath $targetLua -Destination (Join-Path $backupPath 'sle.lua')
Copy-Item -LiteralPath $enabledPath -Destination (Join-Path $backupPath 'enabled.txt')
[IO.File]::WriteAllText($targetLua,$newLua,$encoding)
[IO.File]::WriteAllText($enabledPath,$newEnabled,$encoding)
Write-Output 'Cabine desativada e seu bloco Lua removido. Os modelos, fontes e backups foram preservados.'
