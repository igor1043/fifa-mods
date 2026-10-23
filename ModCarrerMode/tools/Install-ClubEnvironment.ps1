[CmdletBinding()]
param([string]$GameDirectory = (Join-Path $PSScriptRoot '..\..'),[switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$game=(Resolve-Path -LiteralPath $GameDirectory).Path
if (Get-Process -Name FIFA16 -ErrorAction SilentlyContinue) { throw 'Feche o FIFA antes de instalar/verificar este complemento.' }
$manifest=Get-Content -LiteralPath (Join-Path $game 'ModCarrerMode\source\club_environment\assets-manifest.json') -Raw | ConvertFrom-Json
$code=Get-Content -LiteralPath (Join-Path $game 'ModCarrerMode\source\club_environment\release-manifest.json') -Raw | ConvertFrom-Json
foreach($entry in @($manifest.files)+@($code.files)) {
    $target=[IO.Path]::GetFullPath((Join-Path $game $entry.path))
    if (-not $target.StartsWith($game.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Caminho de asset invalido.' }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Extraia o ZIP do ambiente do clube: falta $($entry.path)" }
    if ((Get-Item -LiteralPath $target).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Asset diferente do manifesto: $($entry.path)" }
}
$mode=if($VerifyOnly){'--club-environment-check'}else{'--club-environment-install'}
$process=Start-Process -FilePath (Join-Path $game 'Server16Python.exe') -ArgumentList @($mode,'--game-root',('"'+$game+'"')) -WindowStyle Hidden -Wait -PassThru
if($process.ExitCode -ne 0){throw 'O Server16 nao concluiu a preparacao. Confira ModCarrerMode\runtime\club_environment.'}
if(-not $VerifyOnly) {
    $enabled=Join-Path $game 'ModCarrerMode\mods\enabled.txt'
    $before=[IO.File]::ReadAllText($enabled)
    $after=[regex]::Replace($before,'(?mi)^[ \t]*_local_dressing_room[\\/][^\r\n]+\r?\n?','')
    if($after -notmatch '(?mi)^club_environment[\\/]native_dressing_room\.dll[ \t]*$') { $after=$after.TrimEnd()+"`r`nclub_environment\native_dressing_room.dll`r`n" }
    if($before -ne $after) {
        $backup=Join-Path $game ('ModCarrerMode\backups\club_enabled_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'.txt')
        New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($backup)) -Force | Out-Null
        [IO.File]::WriteAllText($backup,$before,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText($enabled,$after,[Text.UTF8Encoding]::new($false))
    }
}
Write-Output 'Ambiente do clube verificado. Inicie o jogo pelo Server16 atualizado.'
