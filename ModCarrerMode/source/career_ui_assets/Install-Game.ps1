param([string]$GameDirectory='U:\fifa 16')
$ErrorActionPreference='Stop'
if(Get-Process FIFA16 -ErrorAction SilentlyContinue){throw 'Feche o FIFA normalmente antes de instalar.'}
$taskRepo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$taskPlugin=Join-Path $GameDirectory 'ModCarrerMode\mods\career_ui_assets'
New-Item -ItemType Directory -Path $taskPlugin -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $taskRepo 'ModCarrerMode\mods\career_ui_assets\career_ui_assets.dll') -Destination (Join-Path $taskPlugin 'career_ui_assets.dll') -Force
Copy-Item -LiteralPath (Join-Path $taskRepo 'dinput8.dll') -Destination (Join-Path $GameDirectory 'dinput8.dll') -Force
$taskList=Join-Path $GameDirectory 'ModCarrerMode\mods\enabled.txt'
$taskText=[IO.File]::ReadAllText($taskList)
if($taskText -notmatch '(?m)^career_ui_assets\\career_ui_assets\.dll\s*$'){
    [IO.File]::AppendAllText($taskList,"`r`n# Dynamic career competition icons using existing artwork.`r`ncareer_ui_assets\career_ui_assets.dll`r`n",[Text.UTF8Encoding]::new($false))
}
foreach($taskRelative in @('dinput8.dll','ModCarrerMode\mods\career_ui_assets\career_ui_assets.dll')){
    if((Get-FileHash (Join-Path $taskRepo $taskRelative)).Hash -ne (Get-FileHash (Join-Path $GameDirectory $taskRelative)).Hash){throw "Hash mismatch: $taskRelative"}
}
Write-Output 'DLL principal e módulo de ícones instalados. Reinicie o FIFA para testar.'
