[CmdletBinding()]
param([string]$GameDirectory=(Split-Path -Parent $PSScriptRoot),[switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$utf8=[Text.UTF8Encoding]::new($false)
$game=[IO.Path]::GetFullPath($GameDirectory).TrimEnd('\')
$package=[IO.Path]::GetFullPath($PSScriptRoot)
$manifest=Get-Content -LiteralPath (Join-Path $package 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function ByteHash([byte[]]$bytes) {
    $hasher=[Security.Cryptography.SHA256]::Create()
    try{return [BitConverter]::ToString($hasher.ComputeHash($bytes)).Replace('-','')}finally{$hasher.Dispose()}
}
function FileHash([string]$path) {
    $stream=[IO.File]::OpenRead($path);$hasher=[Security.Cryptography.SHA256]::Create()
    try{return [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','')}finally{$stream.Dispose();$hasher.Dispose()}
}
function SafePath([string]$root,[string]$relative) {
    $path=[IO.Path]::GetFullPath((Join-Path $root $relative))
    if(-not $path.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Caminho fora da pasta: $relative"}
    return $path
}
if(-not (Test-Path -LiteralPath (Join-Path $game 'fifa16.exe'))){throw 'Extraia este pacote na pasta do FIFA 16 ou informe -GameDirectory.'}
if(-not (Test-Path -LiteralPath (Join-Path $game 'dinput8_l9_chain.dll')) -and -not (Test-Path -LiteralPath (Join-Path $game 'dinput8_orig.dll'))){throw 'Este complemento requer a base FIFA Friends V12 instalada.'}
foreach($process in Get-Process -Name FIFA16,Server16Python -ErrorAction SilentlyContinue) {
    try{$path=$process.Path}catch{throw 'Nao foi possivel conferir o processo do jogo. Feche FIFA e Server16.'}
    if($path -and [IO.Path]::GetDirectoryName($path).TrimEnd('\') -ieq $game){throw 'Feche FIFA e Server16 desta instalacao antes de atualizar.'}
}
$changes=[Collections.Generic.List[object]]::new()
foreach($entry in $manifest.files) {
    $source=SafePath (Join-Path $package 'payload') $entry.path
    $target=SafePath $game $entry.path
    if(-not (Test-Path -LiteralPath $source -PathType Leaf) -or (Get-Item -LiteralPath $source).Length -ne $entry.bytes -or (FileHash $source) -ine $entry.sha256){throw "Pacote incompleto ou corrompido: $($entry.path)"}
    if($entry.policy -eq 'preserve' -and (Test-Path -LiteralPath $target)){continue}
    $bytes=[IO.File]::ReadAllBytes($source)
    if($entry.policy -eq 'subson_options' -and (Test-Path -LiteralPath $target)) {
        $text=[IO.File]::ReadAllText($target)
        foreach($setting in @(@('BENCH_SIZE','12'),@('MIN_PLAYERS','11'))) {
            $pattern='(?mi)^\s*'+$setting[0]+'\s*=[^\r\n]*'
            if([regex]::Matches($text,$pattern).Count -ne 1){throw 'SubsOn.ini precisa de uma unica chave BENCH_SIZE e MIN_PLAYERS.'}
            $text=[regex]::Replace($text,$pattern,($setting[0]+'='+$setting[1]))
        }
        $bytes=$utf8.GetBytes($text)
    }
    if((Test-Path -LiteralPath $target) -and (FileHash $target) -eq (ByteHash $bytes)){continue}
    $changes.Add(@{path=$entry.path;target=$target;bytes=$bytes})
}
# Merge the background component into each recipient's navigation file.
# The standalone panorama never replaces career cards or their routes.
foreach($nav in $manifest.navigation) {
    $target=SafePath $game $nav.path
    if(-not (Test-Path -LiteralPath $target)){throw "Falta a navegacao da base V12: $($nav.path)"}
    $planned=@($changes | Where-Object path -eq $nav.path)
    $text=if($planned.Count){$utf8.GetString($planned[0].bytes)}else{[IO.File]::ReadAllText($target)}
    $anchor=[regex]::Matches($text,('"name"\s*:\s*"'+[regex]::Escape($nav.state)+'"'))
    if($anchor.Count -ne 1){throw "Estado de navegacao ambiguo: $($nav.state)"}
    $start=$text.IndexOf('"onEnter"',$anchor[0].Index+$anchor[0].Length)
    $end=$text.IndexOf('"onExit"',$start)
    if($start -lt 0 -or $end -lt $start -or $end-$start -gt 6000){throw 'Formato de navegacao nao reconhecido.'}
    $part=$text.Substring($start,$end-$start)
    if($part -notmatch '\[\s*"loadView"\s*,\s*\[\s*"background"\s*,\s*"FIFA"\s*,\s*"BOOTFLOW"\s*\]\s*\]') {
        $pattern='\[\s*"loadView"\s*,\s*\[\s*"background"\s*,\s*"BOOTFLOW"\s*\]\s*\]'
        if([regex]::Matches($part,$pattern).Count -ne 1){throw "Componente de fundo nao reconhecido: $($nav.state)"}
        $part=[regex]::Replace($part,$pattern,'["loadView",["background", "FIFA", "BOOTFLOW"]]')
        $text=$text.Substring(0,$start)+$part+$text.Substring($end)
        if($planned.Count){$planned[0].bytes=$utf8.GetBytes($text)}else{$changes.Add(@{path=$nav.path;target=$target;bytes=$utf8.GetBytes($text)})}
    }
}
$enabledRelative='ModCarrerMode/mods/enabled.txt';$enabled=SafePath $game $enabledRelative
$lines=if(Test-Path -LiteralPath $enabled){[IO.File]::ReadAllLines($enabled)}else{@()}
$owned=@($manifest.enabled | ForEach-Object {($_ -split '[\\/]')[0]})
$lines=@($lines | Where-Object { $trim=$_.Trim(); -not ($trim -and -not $trim.StartsWith('#') -and ($owned -contains ($trim -split '[\\/]')[0])) })
$newText=($lines -join "`r`n").TrimEnd()+"`r`n"+($manifest.enabled -join "`r`n")+"`r`n"
if(-not (Test-Path -LiteralPath $enabled) -or [IO.File]::ReadAllText($enabled) -cne $newText){$changes.Add(@{path=$enabledRelative;target=$enabled;bytes=$utf8.GetBytes($newText)})}
if($VerifyOnly){Write-Output ("Pacote verificado: {0} arquivos; {1} atualizacoes previstas; modo {2}." -f $manifest.files.Count,$changes.Count,$manifest.kind);return}
$backup=SafePath $game ('ModCarrerMode/backups/portable_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$applied=[Collections.Generic.List[object]]::new()
try {
    foreach($change in $changes) {
        $change.existed=Test-Path -LiteralPath $change.target
        if($change.existed){$saved=SafePath $backup $change.path;New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($saved)) -Force | Out-Null;[IO.File]::Copy($change.target,$saved,$false)}
        New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($change.target)) -Force | Out-Null
        $applied.Add($change)
        [IO.File]::WriteAllBytes($change.target,$change.bytes)
        if((FileHash $change.target) -ne (ByteHash $change.bytes)){throw 'Falha na verificacao apos copiar.'}
    }
    $server=Join-Path $game 'Server16Python.exe'
    if($manifest.kind -eq 'club') {
        $job=Start-Process -FilePath $server -ArgumentList @('--club-environment-check','--game-root',('"'+$game+'"')) -WindowStyle Hidden -Wait -PassThru
        if($job.ExitCode -ne 0){throw 'O auxiliar do ambiente nao passou na verificacao.'}
    }
    $mode=if($manifest.kind -eq 'club'){'--activate-career-ui'}else{'--activate-panorama-ui'}
    $job=Start-Process -FilePath $server -ArgumentList @($mode,'--game-root',('"'+$game+'"')) -WindowStyle Hidden -Wait -PassThru
    if($job.ExitCode -ne 0){throw 'A ativacao da interface nao terminou. Confira os diagnosticos do Server16.'}
    [IO.File]::WriteAllText((Join-Path $backup 'installation.json'),(@{kind=$manifest.kind;files=@($changes | ForEach-Object path);completed=$true}|ConvertTo-Json -Depth 4),$utf8)
} catch {
    foreach($change in @($applied.ToArray()) | Sort-Object { [array]::IndexOf($applied.ToArray(),$_) } -Descending) {
        if($change.existed){[IO.File]::Copy((SafePath $backup $change.path),$change.target,$true)}else{Remove-Item -LiteralPath $change.target -Force}
    }
    throw
}
Write-Output "Instalacao concluida. Backup: $backup"
Write-Output 'Abra o Server16 atualizado e inicie o FIFA novamente.'
