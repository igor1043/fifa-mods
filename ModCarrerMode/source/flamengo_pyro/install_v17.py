from pathlib import Path
import shutil,datetime,json,hashlib,re
p=Path(__file__).parent
game=Path(r'U:\fifa 16')
package=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010\v17_teste')
package.mkdir(exist_ok=True)
backup=package/('backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
enabled=game/'ModCarrerMode'/'mods'/'enabled.txt';old=enabled.read_bytes()
shutil.copy2(enabled,backup/'enabled.txt')
mod=game/'ModCarrerMode'/'mods'/'flamengo_pyro';mod.mkdir(exist_ok=True)
assets=game/'data'/'sceneassets'/'particles';assets.mkdir(parents=True,exist_ok=True)
files=[(p/'build'/'flamengo_pyro_v17.dll',mod/'flamengo_pyro_v17.dll')]
files += [(p/'build'/'assets'/name,assets/name) for name in ('flamengo_v17_1043.lnx','flamengo_v17_1043.rx3')]
manifest=[]
for src,dest in files:
    if dest.exists():shutil.copy2(dest,backup/dest.name)
    shutil.copy2(src,dest);shutil.copy2(src,package/src.name)
    assert src.read_bytes()==dest.read_bytes()
    manifest.append({'installed':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
config='[pyro]\r\nenabled=1\r\nautomatic=1\r\n; Automatico: abertura e gols do Flamengo. Sem teclas.\r\n; Teste: abertura 60s; gols 25s.\r\n'
if (mod/'pyro.ini').exists():shutil.copy2(mod/'pyro.ini',backup/'pyro.ini')
(mod/'pyro.ini').write_bytes(config.encode());(package/'pyro.ini').write_bytes(config.encode())
updated=re.sub(rb'(?m)^[ \t]*flamengo_pyro\\flamengo_pyro_v\d+\.dll[ \t]*\r?\n?',b'',old)
line=b'flamengo_pyro\\flamengo_pyro_v17.dll'
enabled.write_bytes(updated+b'\r\n# Flamengo pyro v17: automatic intro and Flamengo goals; opening 60 seconds; goals 25 seconds.\r\n'+line+b'\r\n')
before=[x.strip() for x in old.splitlines() if x.strip() and not x.lstrip().startswith(b'#') and b'flamengo_pyro\\' not in x]
after=[x.strip() for x in enabled.read_bytes().splitlines() if x.strip() and not x.lstrip().startswith(b'#') and b'flamengo_pyro\\' not in x]
assert before==after
disable='''$ErrorActionPreference = 'Stop'
$path = 'U:\\fifa 16\\ModCarrerMode\\mods\\enabled.txt'
$bytes = [System.IO.File]::ReadAllBytes($path)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
$updated = [regex]::Replace($text, '(?m)^[ \\t]*flamengo_pyro\\\\flamengo_pyro_v\\d+\\.dll[ \\t]*\\r?\\n?', '')
if ($updated -ne $text) {
    [System.IO.File]::WriteAllBytes($path + '.before_disable_pyro.bak', $bytes)
    [System.IO.File]::WriteAllText($path, $updated, [System.Text.UTF8Encoding]::new($false))
}
Write-Host 'Modulo de fogos desativado. Feche e abra o FIFA para aplicar.'
'''
for folder in (mod,package):
    (folder/'DESATIVAR.ps1').write_text(disable)
    (folder/'DESATIVAR.cmd').write_text('@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0DESATIVAR.ps1"\npause\n')
manifest.append({'enabled_backup':str(backup/'enabled.txt'),'effect_default':'enabled','automatic_after_enable':True})
(package/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Installed v17, effects automatic by default; unrelated enabled modules preserved')
