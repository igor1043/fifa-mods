[CmdletBinding()]
param(
    [string]$Root
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Split-Path -Parent $PSScriptRoot
}

function Assert-Equal {
    param(
        [string]$Actual,
        [string]$Expected,
        [string]$Label
    )

    if ($Actual -ne $Expected) {
        throw "$Label invalido. Esperado: $Expected. Atual: $Actual."
    }
}

function Assert-Contains {
    param(
        [string]$Text,
        [string]$Needle,
        [string]$Label
    )

    if ($Text.IndexOf($Needle, [StringComparison]::Ordinal) -lt 0) {
        throw "$Label nao contem '$Needle'."
    }
}

$l9Resource = Join-Path $Root 'ModCarrerMode\source\career_native\build\active_chain_resource.bin'
$entryDll = Join-Path $Root 'dinput8.dll'
$config = Join-Path $Root 'dinput8_L9.ini'
$winmm = Join-Path $Root 'winmm.dll'

foreach ($path in @($l9Resource, $entryDll, $config, $winmm)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Arquivo obrigatorio ausente: $path"
    }
}

Assert-Equal (Get-FileHash -LiteralPath $l9Resource -Algorithm SHA256).Hash `
    'B6583FC60B5058215B12E90E49E5F1D2A0B5069AA909EAB9B916621AD77AC6E2' `
    'Recurso L9.65'
Assert-Equal (Get-FileHash -LiteralPath $winmm -Algorithm SHA256).Hash `
    'B43513DDEAB5F9F0904EB76E4CB543596CA35B1AAAE3C60CE7993061B7AC1A0E' `
    'CompData Patcher WinMM'

$configText = Get-Content -LiteralPath $config -Raw
foreach ($needle in @(
    '[Saisonziele]', '[ScoutRegionen]', '[Ligenblock]', '[Turnierliste]',
    '[SpielerCache]', '[NullGetter]', '[Tokenpool]', '[Knotenablage]',
    '[Formationsgrenze]')) {
    Assert-Contains $configText $needle 'Configuracao L9'
}

$entryText = [Text.Encoding]::ASCII.GetString(
    [IO.File]::ReadAllBytes($entryDll))
Assert-Contains $entryText 'FIFA 16 dinput8 L9.65' 'DLL de entrada compilada'

Write-Output 'OK: recurso L9, configuracao, WinMM e DLL de entrada validados.'
