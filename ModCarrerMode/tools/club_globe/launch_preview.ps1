param([switch]$ServerOnly)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$ready=$false
try{$ready=(Invoke-RestMethod 'http://127.0.0.1:8876/api/health' -TimeoutSec 2).service -eq 'fifa-friends-career-preview'}catch{}
if(-not $ready){
 $python=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
 if(-not (Test-Path -LiteralPath $python)){$python=(Get-Command python.exe -ErrorAction Stop).Source}
 Start-Process -FilePath $python -ArgumentList @('-X','utf8','"'+(Join-Path $root 'preview_server.py')+'"') -WorkingDirectory $root -WindowStyle Hidden
}
if(-not $ServerOnly){Start-Process 'http://127.0.0.1:8876/home.html'}
