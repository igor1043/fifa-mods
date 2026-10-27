param(
    [string]$InputVideo = 'C:\Users\igorv\OneDrive\Área de Trabalho\video teste.mp4',
    [string]$LegacyFFmpeg = 'J:\mods\fifa 16\3DGameDevBlog\Data\ffmpeg.exe'
)
$ErrorActionPreference = 'Stop'
$package = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\mods\vp8_compat'))
New-Item -ItemType Directory -Path $package -Force | Out-Null
$outputVideo = Join-Path $package 'test_1080p_high.vp8'
if (Test-Path -LiteralPath $outputVideo) { throw 'Output already exists; preserve it before making another candidate.' }
& $LegacyFFmpeg -hide_banner -nostdin -n -i $InputVideo -map 0:v:0 -map 0:a:0 -map_metadata -1 -vf 'fps=2997/100,format=yuv420p' -c:v libvpx -deadline good -cpu-used 4 -crf 4 -b:v 8M -auto-alt-ref 0 -lag-in-frames 0 -g 60 -c:a libvorbis -q:a 6 -ar 48000 -ac 2 -cluster_time_limit 1000 -f webm $outputVideo
if ($LASTEXITCODE -ne 0) { throw 'Conversion failed; do not install the candidate.' }
