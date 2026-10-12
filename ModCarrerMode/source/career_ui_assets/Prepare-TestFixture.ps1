$ErrorActionPreference = 'Stop'
# Synthetic transparent DDS data exercises the loader without shipping game art.
$icons = Join-Path $PSScriptRoot 'build\fixture\data\ui\imgAssets\careerCompetitionIcons'
New-Item -ItemType Directory -Force -Path $icons | Out-Null
$dds = New-Object byte[] 16512
[Text.Encoding]::ASCII.GetBytes('DDS ').CopyTo($dds, 0)
foreach ($field in @(@(4,124), @(8,0x81007), @(12,128), @(16,128), @(20,16384), @(76,32), @(80,4), @(108,0x1000))) {
    [BitConverter]::GetBytes([uint32]$field[1]).CopyTo($dds, [int]$field[0])
}
[Text.Encoding]::ASCII.GetBytes('DXT5').CopyTo($dds, 84)
foreach ($name in @('c1693.dds', 'c820.dds')) { [IO.File]::WriteAllBytes((Join-Path $icons $name), $dds) }
[IO.File]::WriteAllText((Join-Path $icons 'c1700.dds'), 'invalid DDS')
[IO.File]::WriteAllText((Join-Path $icons 'index.tsv'), "1693`t0`n820`t1`n", [Text.UTF8Encoding]::new($false))
