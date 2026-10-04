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
$config=Join-Path $fixture 'ModCarrerMode\career_native_mode.ini'
[IO.File]::WriteAllText($config,'[native]'+[Environment]::NewLine+'mode=trace')
$snapshot=Join-Path $fixture 'ModCarrerMode\injury_snapshot.tsv'
[IO.File]::WriteAllText($snapshot,'fixture injury snapshot')
$private=Join-Path $fixture 'ModCarrerMode\runtime\operations\preserve.bin'
[IO.File]::WriteAllBytes($private,[byte[]](1,2,3,4))
$db=Join-Path $fixture 'data\loc\por_br.db'
[IO.File]::WriteAllBytes($db,[byte[]](5,6,7,8))
$hashes=@{Config=(Get-FileHash -LiteralPath $config).Hash;Snapshot=(Get-FileHash -LiteralPath $snapshot).Hash;Private=(Get-FileHash -LiteralPath $private).Hash;DB=(Get-FileHash -LiteralPath $db).Hash}
& (Join-Path $PSScriptRoot 'Install-Game.ps1') -GameDirectory $fixture -BackupDirectory (Join-Path $fixture 'installer-backups')
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
Write-Output "PASS: pacote completo, configuracoes/DB/contratos preservados, migracao, restauracao opcional e reinstalacao idempotente. Fixture: $fixture"
