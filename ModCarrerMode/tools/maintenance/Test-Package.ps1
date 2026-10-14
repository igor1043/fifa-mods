[CmdletBinding()]
param([string]$FixtureDirectory = ('J:\mods\backup\ModCarrerMode_PackageTest_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')))
$ErrorActionPreference='Stop'
$fixture=[IO.Path]::GetFullPath($FixtureDirectory)
if (-not $fixture.StartsWith('J:\mods\backup\ModCarrerMode_PackageTest_',[StringComparison]::OrdinalIgnoreCase)) { throw 'Este teste aceita somente sua pasta isolada de fixture.' }
if (Test-Path -LiteralPath $fixture) { throw 'A fixture precisa ser nova.' }
$mod=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$repo=[IO.Directory]::GetParent($mod).FullName
New-Item -ItemType Directory -Path $fixture | Out-Null
# A marker file, never executed; this is NOT a real FIFA installation.
[IO.File]::WriteAllBytes((Join-Path $fixture 'FIFA16.exe'),[byte[]](0,0,0))
foreach($folder in @('ModCarrerMode\runtime\operations','data\loc')) { New-Item -ItemType Directory -Force -Path (Join-Path $fixture $folder) | Out-Null }
foreach($name in @('model.rx3','textures.rx3')) {
    $local=Join-Path $fixture ('data\sceneassets\var_cabin\'+$name)
    New-Item -ItemType Directory -Force -Path (Split-Path $local) | Out-Null
    # The fixture never runs FIFA or loads these marker assets.
    [IO.File]::WriteAllText($local,'preserved local VAR fixture '+$name)
}
# Check this isolated installation while the real game may still be open.
function Get-Process { param([string]$Name,[string]$ErrorAction) return $null }
$config=Join-Path $fixture 'ModCarrerMode\career_native_mode.ini'
[IO.File]::WriteAllText($config,'[native]'+[Environment]::NewLine+'mode=trace')
$snapshot=Join-Path $fixture 'ModCarrerMode\injury_snapshot.tsv'
[IO.File]::WriteAllText($snapshot,'fixture injury snapshot')
$private=Join-Path $fixture 'ModCarrerMode\runtime\operations\preserve.bin'
[IO.File]::WriteAllBytes($private,[byte[]](1,2,3,4))
$db=Join-Path $fixture 'data\loc\por_br.db'
[IO.File]::WriteAllBytes($db,[byte[]](5,6,7,8))
$hashes=@{Config=(Get-FileHash -LiteralPath $config).Hash;Snapshot=(Get-FileHash -LiteralPath $snapshot).Hash;Private=(Get-FileHash -LiteralPath $private).Hash;DB=(Get-FileHash -LiteralPath $db).Hash}
# Simulate an upgrade from a package with inactive historical DLLs.
$legacyFiles = @(
    'skip_server_shutdown_notice\skip_server_shutdown_notice.dll',
    'kickoff_modern_v20\kickoff_modern_v20.dll',
    'kickoff_modern_restore_v18\kickoff_modern_restore_v18.dll',
    'multiball_visual\multiball_visual_v16.dll',
    'multiball_visual\multiball_visual_v3.dll',
    'mascot_single\mascot_goal_line_v28.dll',
    'mascot_single\mascot_corner.dll',
    'mascot_single\animation_command.txt',
    'bench_native12\bench_native12_v5.dll',
    'enabled.txt.before-test.bak',
    'enabled_birthdate_2006.txt'
)
$legacyHashes = @{}
foreach ($relative in $legacyFiles) {
    $path = Join-Path $fixture ('ModCarrerMode\mods\'+$relative)
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($path)) | Out-Null
    [IO.File]::WriteAllText($path,'legacy fixture: '+$relative)
    $legacyHashes[$relative] = (Get-FileHash -LiteralPath $path).Hash
}
$customPlugin = Join-Path $fixture 'ModCarrerMode\mods\custom_module\custom.dll'
New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($customPlugin)) | Out-Null
[IO.File]::WriteAllBytes($customPlugin,[byte[]](20,21,22))
$customHash = (Get-FileHash -LiteralPath $customPlugin).Hash
$localIcons = Join-Path $fixture 'data\ui\imgAssets\careerCompetitionIcons'
New-Item -ItemType Directory -Force -Path $localIcons | Out-Null
$localDds = Join-Path $localIcons 'c9999.dds'
$localIndex = Join-Path $localIcons 'index.tsv'
[IO.File]::WriteAllText($localDds, 'user-edited local icon')
[IO.File]::WriteAllText($localIndex, "9999`t1`n")
$localDdsHash = (Get-FileHash -LiteralPath $localDds).Hash
$localIndexHash = (Get-FileHash -LiteralPath $localIndex).Hash
& (Join-Path $PSScriptRoot 'Install-Game.ps1') -GameDirectory $fixture -BackupDirectory (Join-Path $fixture 'installer-backups')
if ((Get-FileHash -LiteralPath $localDds).Hash -ne $localDdsHash -or (Get-FileHash -LiteralPath $localIndex).Hash -ne $localIndexHash) { throw 'Icone local ou suas regras de disponibilidade alterados.' }
foreach ($relative in $legacyFiles) {
    if (Test-Path -LiteralPath (Join-Path $fixture ('ModCarrerMode\mods\'+$relative))) { throw "Revisao antiga permaneceu instalada: $relative" }
    $saved = @(Get-ChildItem -LiteralPath (Join-Path $fixture 'installer-backups') -Recurse -File | Where-Object { $_.FullName.EndsWith('\edition-switch\ModCarrerMode\mods\'+$relative,[StringComparison]::OrdinalIgnoreCase) })
    if ($saved.Count -ne 1 -or (Get-FileHash -LiteralPath $saved[0].FullName).Hash -ne $legacyHashes[$relative]) { throw "Backup historico ausente/divergente: $relative" }
}
if ((Get-FileHash -LiteralPath $customPlugin).Hash -ne $customHash) { throw 'Mod adicional do usuario alterado.' }
& (Join-Path $PSScriptRoot 'Verify-Package.ps1') -PackageRoot $fixture
# A disabled revision must also fail package verification.
$invalidDll = Join-Path $fixture 'ModCarrerMode\mods\mascot_single\mascot_goal_line_v99.dll'
[IO.File]::WriteAllBytes($invalidDll,[byte[]](0,0,0))
$rejected = $false
try { & (Join-Path $PSScriptRoot 'Verify-Package.ps1') -PackageRoot $fixture | Out-Null }
catch { if ($_.Exception.Message -like 'Revisao antiga/backup*') { $rejected = $true } else { throw } }
Remove-Item -LiteralPath $invalidDll
if (-not $rejected) { throw 'Verificador aceitou uma DLL historica desabilitada.' }
$invalidDll = Join-Path $fixture 'ModCarrerMode\mods\mascot_single\extra.dll'
[IO.File]::WriteAllBytes($invalidDll,[byte[]](0,0,0))
$rejected = $false
try { & (Join-Path $PSScriptRoot 'Verify-Package.ps1') -PackageRoot $fixture | Out-Null }
catch { if ($_.Exception.Message -like 'Mais de uma DLL no pacote*') { $rejected = $true } else { throw } }
Remove-Item -LiteralPath $invalidDll
if (-not $rejected) { throw 'Verificador aceitou duas DLLs do mesmo mod.' }
$newConfig=Join-Path $fixture 'ModCarrerMode\config\career_native_mode.ini'
$newSnapshot=Join-Path $fixture 'ModCarrerMode\runtime\injury_snapshot.tsv'
if ((Get-FileHash -LiteralPath $newConfig).Hash -ne $hashes.Config) { throw 'Configuracao pessoal alterada.' }
if ((Get-FileHash -LiteralPath $newSnapshot).Hash -ne $hashes.Snapshot) { throw 'Snapshot alterado.' }
if ((Get-FileHash -LiteralPath $private).Hash -ne $hashes.Private) { throw 'Estado privado alterado.' }
if ((Get-FileHash -LiteralPath $db).Hash -ne $hashes.DB) { throw 'DB sobrescrito sem solicitar restauracao.' }
if (Test-Path -LiteralPath (Join-Path $fixture 'ModCarrerMode\source')) { throw 'Fontes instaladas indevidamente.' }
if ((Get-FileHash -LiteralPath (Join-Path $fixture 'dinput8.dll')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $repo 'dinput8.dll')).Hash) { throw 'DLL incorreta.' }
if (-not (Test-Path -LiteralPath (Join-Path $fixture 'ModCarrerMode\crowd.ini'))) { throw 'Configuracao do plugin legado ausente.' }
& (Join-Path $PSScriptRoot 'Install-Game.ps1') -GameDirectory $fixture -BackupDirectory (Join-Path $fixture 'installer-backups') -RestoreLocalization
if ((Get-FileHash -LiteralPath $db).Hash -ne (Get-FileHash -LiteralPath (Join-Path $repo 'data\loc\por_br.db')).Hash) { throw 'Restauracao opcional da localizacao falhou.' }
$result=& (Join-Path $PSScriptRoot 'Install-Game.ps1') -GameDirectory $fixture -VerifyOnly
if ($result[0].ToInstall -ne 0) { throw 'Instalacao nao e idempotente.' }
Write-Output "PASS: pacote completo, uma DLL por mod, revisoes antigas arquivadas com hashes preservados, mods adicionais/configuracoes/DB/contratos preservados, restauracao opcional e reinstalacao idempotente. Fixture: $fixture"
