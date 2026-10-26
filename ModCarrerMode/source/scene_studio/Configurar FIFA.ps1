$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
$studioPicker=New-Object System.Windows.Forms.FolderBrowserDialog
$studioPicker.Description='Selecione a raiz do FIFA 16. A bancada apenas lê os modelos base para exportar RX3.'
if($studioPicker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){exit}
$studioGame=$studioPicker.SelectedPath
if(-not(Test-Path -LiteralPath (Join-Path $studioGame 'fifa16.exe'))){throw 'Escolha a pasta que contém fifa16.exe.'}
@{game_root=$studioGame} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'settings.json') -Encoding UTF8
[System.Windows.Forms.MessageBox]::Show('Pasta configurada. A bancada não instala nem altera arquivos no FIFA.','FIFA Friends') | Out-Null
