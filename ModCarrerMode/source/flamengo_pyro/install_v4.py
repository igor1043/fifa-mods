from pathlib import Path
import datetime,hashlib,json,shutil
root=Path(__file__).parent
game=Path(r'U:\fifa 16')
study=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010')
package=study/'v4_teste'
package.mkdir(exist_ok=True)
backup=package/('backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir()
enabled=game/'ModCarrerMode'/'mods'/'enabled.txt'
old=enabled.read_bytes()
original_bytes=old
shutil.copy2(enabled,backup/'enabled.txt')
import re
old=re.sub(rb'(?m)^flamengo_pyro\\flamengo_pyro_v[23]\.dll\r?\n?',b'',old)
target=game/'ModCarrerMode'/'mods'/'flamengo_pyro'
target.mkdir(exist_ok=True)
assets=game/'data'/'sceneassets'/'particles'
assets.mkdir(parents=True,exist_ok=True)
pairs=[(root/'build'/'flamengo_pyro_v4.dll',target/'flamengo_pyro_v4.dll')]
pairs += [(root/'build'/'assets'/n,assets/n) for n in ('flamengo_1043.lnx','flamengo_1043.rx3')]
manifest=[]
for source,dest in pairs:
    if dest.exists():shutil.copy2(dest,backup/dest.name)
    shutil.copy2(source,dest)
    assert dest.read_bytes()==source.read_bytes()
    shutil.copy2(source,package/source.name)
    manifest.append({'installed':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
line=b'flamengo_pyro\\flamengo_pyro_v4.dll'
if line not in [x.strip() for x in old.splitlines()]:
    enabled.write_bytes(old+(b'\r\n' if not old.endswith(b'\n') else b'')+b'\r\n# Experimental Flamengo 1043 sideline particles, 30 seconds; F8 replay.\r\n'+line+b'\r\n')
assert line in [x.strip() for x in enabled.read_bytes().splitlines()]
manifest.append({'enabled_backup':str(backup/'enabled.txt'),'previous_enabled_sha256':hashlib.sha256(original_bytes).hexdigest()})
(package/'manifest.json').write_text(json.dumps(manifest,indent=2))
disable='''$ErrorActionPreference = 'Stop'
$enabledPath = 'U:\\fifa 16\\ModCarrerMode\\mods\\enabled.txt'
$targetLine = 'flamengo_pyro\\flamengo_pyro_v4.dll'
$bytes = [System.IO.File]::ReadAllBytes($enabledPath)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
$pattern = '(?m)^[ \\t]*' + [regex]::Escape($targetLine) + '[ \\t]*\\r?\\n?'
$updated = [regex]::Replace($text, $pattern, '')
if ($updated -ne $text) {
    [System.IO.File]::WriteAllBytes($enabledPath + '.before_disable_pyro.bak', $bytes)
    [System.IO.File]::WriteAllText($enabledPath, $updated, [System.Text.UTF8Encoding]::new($false))
}
Write-Host 'Flamengo pyro desativado. Feche e abra o FIFA para aplicar.'
'''
for folder in (target,package):
    (folder/'DESATIVAR.ps1').write_text(disable)
    (folder/'DESATIVAR.cmd').write_text('@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0DESATIVAR.ps1"\npause\n')
print('Installed',json.dumps(manifest,indent=2))
