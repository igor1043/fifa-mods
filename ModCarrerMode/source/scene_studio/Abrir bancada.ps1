$ErrorActionPreference='Stop'
$poseRoot=$PSScriptRoot
$posePortFile=Join-Path $poseRoot 'server.port'
$poseRunning=$false
if(Test-Path -LiteralPath $posePortFile){
    $posePort=[int](Get-Content -LiteralPath $posePortFile)
    try{$poseHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$posePort/api/health" -TimeoutSec 2;$poseRunning=$poseHealth.application -eq 'fifa-friends-scene-editor'}catch{}
}
if(-not $poseRunning){
    $posePython=Join-Path $poseRoot 'python\python.exe'
    if(-not(Test-Path -LiteralPath $posePython)){
        $poseCommand=Get-Command python -ErrorAction SilentlyContinue
        if(-not $poseCommand){throw 'Extraia o pacote completo da bancada (com Python) ou instale Python 3.13 e as dependências.'}
        $posePython=$poseCommand.Source
    }
    $poseAdapter=Join-Path $poseRoot 'local_ai\adapters.exe'
    if(Test-Path -LiteralPath $poseAdapter){
        try{(& $poseAdapter) | Set-Content -LiteralPath (Join-Path $poseRoot 'local_ai\device.json') -Encoding ascii}catch{}
    }
    Start-Process -FilePath $posePython -ArgumentList @('-B','serve.py') -WorkingDirectory $poseRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $poseRoot 'server.log') -RedirectStandardError (Join-Path $poseRoot 'server-error.log')
    for($poseAttempt=0;$poseAttempt -lt 30;$poseAttempt++){
        Start-Sleep -Milliseconds 200
        if(Test-Path -LiteralPath $posePortFile){
            $posePort=[int](Get-Content -LiteralPath $posePortFile)
            try{$poseHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$posePort/api/health" -TimeoutSec 1;if($poseHealth.application -eq 'fifa-friends-scene-editor'){$poseRunning=$true;break}}catch{}
        }
    }
}
if(-not $poseRunning){throw 'A bancada local não iniciou. Confira server-error.log.'}
Start-Process "http://127.0.0.1:$posePort/index.html"
