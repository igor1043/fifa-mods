$ErrorActionPreference='Stop'
$aiRoot=$PSScriptRoot
$aiCommand=Get-Command python -ErrorAction SilentlyContinue
if(-not $aiCommand){throw 'Use o ZIP portátil completo, ou instale Python 3.13 x64 para preparar as dependências.'}
$aiPython=$aiCommand.Source
& $aiPython -m pip install --target (Join-Path $aiRoot 'vendor') --upgrade --no-deps 'rtmlib==0.0.16'
if($LASTEXITCODE -ne 0){throw 'Não foi possível instalar a biblioteca de poses.'}
& $aiPython -m pip install --target (Join-Path $aiRoot 'vendor') --upgrade -r (Join-Path $aiRoot 'requirements-local.txt')
if($LASTEXITCODE -ne 0){throw 'Não foi possível instalar as dependências locais.'}
& $aiPython -B (Join-Path $aiRoot 'setup_models.py')
if($LASTEXITCODE -ne 0){throw 'Não foi possível preparar os modelos.'}
