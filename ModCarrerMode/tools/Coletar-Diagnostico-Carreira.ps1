# Somente leitura do jogo: gera um ZIP de diagnostico, sem instalar ou corrigir.
[CmdletBinding()]
param([string]$GameRoot, [string]$OutputPath)
$ErrorActionPreference='Stop'
if (-not $GameRoot) {
    $candidate=Get-Item -LiteralPath $PSScriptRoot
    for($i=0; $i -lt 4 -and $candidate; $i++) {
        if(Test-Path -LiteralPath (Join-Path $candidate.FullName 'fifa16.exe')) { $GameRoot=$candidate.FullName; break }
        $candidate=$candidate.Parent
    }
}
if(-not $GameRoot) { $GameRoot=Read-Host 'Pasta onde esta fifa16.exe' }
$gamePath=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\')
if(-not (Test-Path -LiteralPath (Join-Path $gamePath 'ModCarrerMode'))) { throw 'ModCarrerMode nao encontrada nesta pasta.' }
if(-not $OutputPath) { $OutputPath=Join-Path ([Environment]::GetFolderPath('Desktop')) ('FIFA-Diagnostico-Carreira-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.zip') }
$zipPath=[IO.Path]::GetFullPath($OutputPath)
if(Test-Path -LiteralPath $zipPath) { throw 'O ZIP de destino ja existe. Escolha outro nome.' }
$tempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$stagePath=Join-Path $tempBase ('Server16-Diagnostico-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($stagePath) | Out-Null
$files=[Collections.Generic.List[object]]::new()
$expected=@{}
try {
    foreach($manifestName in @('ModCarrerMode/source/club_environment/release-manifest.json','ModCarrerMode/source/club_environment/assets-manifest.json','ModCarrerMode/data/club_browser/assets-manifest.json')) {
        $manifestPath=Join-Path $gamePath $manifestName
        if(Test-Path -LiteralPath $manifestPath) {
            foreach($row in (Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json).files) { $expected[$row.path]=$row }
        }
    }
    $wanted=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($name in $expected.Keys) { [void]$wanted.Add($name) }
    foreach($name in @('fifa16.exe','Server16Python.exe','dinput8.dll','ModCarrerMode/mods/enabled.txt','ModCarrerMode/tools/club_browser/generate_lineup.exe')) { [void]$wanted.Add($name) }
    $enabled=Join-Path $gamePath 'ModCarrerMode/mods/enabled.txt'
    if(Test-Path -LiteralPath $enabled) {
        foreach($line in (Get-Content -LiteralPath $enabled)) {
            $line=$line.Trim()
            if($line -and -not $line.StartsWith('#')) { [void]$wanted.Add('ModCarrerMode/mods/'+$line) }
        }
    }
    foreach($name in ($wanted | Sort-Object)) {
        $path=[IO.Path]::GetFullPath((Join-Path $gamePath $name))
        if(-not $path.StartsWith($gamePath+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Manifesto com caminho fora da pasta do jogo.' }
        $entry=[ordered]@{path=$name;exists=$false}
        if(Test-Path -LiteralPath $path -PathType Leaf) {
            try {
                $item=Get-Item -LiteralPath $path
                $entry.exists=$true; $entry.bytes=$item.Length
                $entry.sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
                if($expected.ContainsKey($name)) { $entry.matches=($entry.sha256 -eq $expected[$name].sha256 -and $entry.bytes -eq $expected[$name].bytes) }
            } catch { $entry.error=$_.Exception.Message }
        }
        $files.Add([pscustomobject]$entry)
    }
    $report=[ordered]@{schema=1;created=(Get-Date).ToString('o');game_root=$gamePath;files=$files;save_or_financial_database_copied=$false}
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stagePath 'installation.json') -Encoding UTF8
    $logs=[Collections.Generic.List[string]]::new()
    foreach($name in @('club_browser.log','career_loader.log','career_stadium_images.log','career_jobs_runtime.log')) { $logs.Add('ModCarrerMode/logs/'+$name) }
    $logs.Add('ModCarrerMode/runtime/club_environment/supervisor.log')
    foreach($name in @('native_room.log','native_status.json','native_asset_helper_r46.log','native_helper_startup.log','worker.log','service.log','room_scene_controls.log')) { $logs.Add('ModCarrerMode/runtime/club_environment/room/runtime/'+$name) }
    $browser=Join-Path $gamePath 'ModCarrerMode/runtime/club_browser'
    if(Test-Path -LiteralPath $browser) {
        foreach($session in (Get-ChildItem -LiteralPath $browser -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 3)) {
            if($session.Name -notmatch '^\d+$') { continue }
            foreach($name in @('worker.log','service.log','launcher.log','engine.log','native_status.json','status.tsv','export.log','timings.json')) { $logs.Add('ModCarrerMode/runtime/club_browser/'+$session.Name+'/'+$name) }
        }
    }
    foreach($name in $logs) {
        $source=Join-Path $gamePath $name
        if(Test-Path -LiteralPath $source -PathType Leaf) {
            $dest=Join-Path $stagePath $name
            [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dest)) | Out-Null
            # Limit each log; do not collect rosters, images, save DATA/INDEX,
            # loans.sqlite or any unrelated file in a runtime directory.
            $inputFile=[IO.File]::Open($source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
            try {
                if($inputFile.Length -gt 2MB) { [void]$inputFile.Seek(-2MB,[IO.SeekOrigin]::End) }
                $outputFile=[IO.File]::Create($dest)
                try { $inputFile.CopyTo($outputFile) } finally { $outputFile.Dispose() }
            } finally { $inputFile.Dispose() }
        }
    }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($zipPath)) | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory($stagePath,$zipPath)
    Write-Output ('Diagnostico criado: '+$zipPath)
    Write-Output ('Arquivos ausentes: '+@($files | Where-Object { -not $_.exists }).Count)
    Write-Output ('Arquivos diferentes do manifesto: '+@($files | Where-Object { $_.PSObject.Properties.Name -contains 'matches' -and -not $_.matches }).Count)
} finally {
    $resolvedStage=[IO.Path]::GetFullPath($stagePath)
    if(-not $resolvedStage.StartsWith($tempBase+'\Server16-Diagnostico-',[StringComparison]::OrdinalIgnoreCase)) { throw 'Pasta temporaria invalida para limpeza.' }
    if(Test-Path -LiteralPath $resolvedStage) { Remove-Item -LiteralPath $resolvedStage -Recurse -Force }
}
