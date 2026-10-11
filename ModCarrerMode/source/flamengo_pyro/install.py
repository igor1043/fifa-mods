"""Install one canonical module; archive previous revision names in the study."""
from pathlib import Path
import shutil,datetime,json,hashlib,re,sys
p=Path(__file__).parent
game=Path(r'U:\fifa 16')
study=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010\v23_presentation_gate')
study.mkdir(exist_ok=True)
backup=study/('backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir()
mod=game/'ModCarrerMode/mods/stadium_pyrotechnics';mod.mkdir(exist_ok=True)
oldmod=game/'ModCarrerMode/mods/flamengo_pyro'
assets=game/'data/sceneassets/particles'
logs=game/'ModCarrerMode/logs'
enabled=game/'ModCarrerMode/mods/enabled.txt'
old=enabled.read_bytes();shutil.copy2(enabled,backup/'enabled.txt')
def archive_path(src):
    rel=src.relative_to(game);dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    return dest
manifest=[]
loaded_relocated=[]
files=[(p/'build/stadium_pyrotechnics.dll',mod/'stadium_pyrotechnics.dll')]
files += [(p/'build/assets'/name,assets/name) for name in ('stadium_pyrotechnics_0.lnx','stadium_pyrotechnics_0.rx3')]
for src,dest in files:
    if dest.exists():shutil.copy2(dest,archive_path(dest))
    try:shutil.copy2(src,dest)
    except PermissionError:
        if dest.suffix.lower()!='.dll':raise
        # Keep the mapped image alive outside the installed mod until game exit.
        hold=p/'historico_carregado';hold.mkdir(exist_ok=True)
        hold_path=hold/(dest.stem+'_'+backup.name+'.dll')
        assert hold_path.resolve().is_relative_to(p.resolve())
        dest.rename(hold_path)
        loaded_relocated.append(str(hold_path))
        shutil.copy2(src,dest)
    shutil.copy2(src,study/src.name)
    assert src.read_bytes()==dest.read_bytes()
    manifest.append({'installed':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
config=mod/'pyro.ini'
if not config.exists() and (oldmod/'pyro.ini').exists():shutil.copy2(oldmod/'pyro.ini',config)
if config.exists():
    shutil.copy2(config,archive_path(config))
else:config.write_text('[pyro]\nenabled=1\nautomatic=1\n',encoding='utf-8')
shutil.copy2(config,study/config.name)

module_re=re.compile(rb'^[ \t]*(?:flamengo_pyro\\flamengo_pyro(?:_v\d+)?|stadium_pyrotechnics\\stadium_pyrotechnics)\.dll[ \t]*$')
comment_re=re.compile(rb'^[ \t]*#[ \t]*(?:Flamengo pyro(?: v\d+)?|Stadium pyrotechnics):',re.I)
lines=old.splitlines(keepends=True)
kept=[line for line in lines if not module_re.match(line.rstrip(b'\r\n')) and not comment_re.match(line)]
updated=b''.join(kept)
if updated and not updated.endswith(b'\n'):updated+=b'\r\n'
updated+=b'\r\n# Stadium pyrotechnics: home colors, opening and home goals; two smoke layers.\r\nstadium_pyrotechnics\\stadium_pyrotechnics.dll\r\n'
def unrelated(data):
    return [x for x in data.splitlines() if x.strip() and not x.lstrip().startswith(b'#') and not module_re.match(x)]
assert unrelated(old)==unrelated(updated)
if sum(bool(module_re.match(x.rstrip(b'\r\n'))) for x in lines)==1 and b'stadium_pyrotechnics\\stadium_pyrotechnics.dll' in old:
    updated=old
assert enabled.read_bytes()==old, 'Loader changed concurrently; retry from current file'
if updated!=old:enabled.write_bytes(updated)

disable=r'''$ErrorActionPreference = 'Stop'
$path = 'U:\fifa 16\ModCarrerMode\mods\enabled.txt'
$bytes = [System.IO.File]::ReadAllBytes($path)
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
$updated = [regex]::Replace($text, '(?m)^[ \t]*stadium_pyrotechnics\\stadium_pyrotechnics\.dll[ \t]*\r?\n?', '')
if ($updated -ne $text) {
    [System.IO.File]::WriteAllBytes($path + '.before_disable_pyro.bak', $bytes)
    [System.IO.File]::WriteAllText($path, $updated, [System.Text.UTF8Encoding]::new($false))
}
Write-Host 'Modulo de fogos desativado. Feche e abra o FIFA para aplicar.'
'''
readme='''Modulo de fogos e fumaca

Arquivo unico: stadium_pyrotechnics.dll.
Efeito e assets: stadium_pyrotechnics_0.lnx / .rx3.
Log: ModCarrerMode/logs/stadium_pyrotechnics.log.
Automatico para qualquer mandante; abertura 60 segundos e gol do mandante 25 segundos.
Previa de selecao, KickOffHub, uniformes e outros menus: sem disparo, abertura rearmada.
Apenas apresentacao real (pagina de carregamento/TV bumper) com duas equipes nativas libera inicio.
Pausa/replay nao arma novos disparos; apenas conserva uma animacao ja iniciada.
Server16: controles independentes em ModCarrerMode/config/match_presentation.ini, sem sobrescrever preferencia.
Cores: duas cores institucionais do mandante recuperadas do banco FIFA instalado.
Gol do visitante nao aciona novos efeitos. Um show ja iniciado segue sua duracao.
Duas camadas de cada fumaca na mesma origem, inclusive rastro do foguete.
Encerramento: fontes diminuem em pares nos ultimos 12 segundos; cauda de 7 segundos incluida na duracao.
Config: pyro.ini, enabled=0 ou 1. Sem teclas F7/F8.
Feche e abra o FIFA para carregar uma atualizacao da DLL.
Depois de carregada, Reiniciar Partida rearma abertura e detector de gols.
Historico e backups ficam na pasta de estudos, fora do mod instalado.
'''
for folder in (mod,study):
    for name,data in [('DESATIVAR.ps1',disable),('DESATIVAR.cmd','@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0DESATIVAR.ps1"\npause\n'),('LEIA-ME.txt',readme)]:
        if folder==mod and (folder/name).exists():shutil.copy2(folder/name,archive_path(folder/name))
        (folder/name).write_text(data,encoding='utf-8')

# Exact scope, no recursive moves: only previous files belonging to this module.
legacy=list(oldmod.glob('flamengo_pyro*.dll'))
legacy += [oldmod/name for name in ('pyro.ini','LEIA-ME.txt','DESATIVAR.ps1','DESATIVAR.cmd') if (oldmod/name).exists()]
# Keep old assets available for a running session's asynchronous/native reloads.
if '--game-closed' in sys.argv:
    legacy+=list(assets.glob('flamengo_v*_1043.lnx'))+list(assets.glob('flamengo_v*_1043.rx3'))
    legacy += [x for x in (assets/'flamengo_1043.lnx',assets/'flamengo_1043.rx3',assets/'flamengo_pyro_1043.lnx',assets/'flamengo_pyro_1043.rx3',logs/'flamengo_pyro.log') if x.exists()]
legacy+=list(logs.glob('flamengo_pyro_v*.log'))
pending=[]
relocated=[]
for src in legacy:
    assert src.parent in (mod,oldmod,assets,logs)
    assert src.is_file()
    target=archive_path(src)
    assert target.is_relative_to(backup)
    try:
        # Both drives may differ: copy and verify before removing the original.
        shutil.copy2(src,target)
        assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
        src.unlink()
    except PermissionError:
        # Windows can rename a mapped DLL even while it forbids deleting it.
        if src.parent in (mod,oldmod):
            hold=p/'historico_carregado';hold.mkdir(exist_ok=True)
            target_hold=hold/(src.stem+'_'+backup.name+src.suffix)
            assert target_hold.parent.resolve().is_relative_to(p.resolve())
            try:
                src.rename(target_hold);relocated.append(str(target_hold));continue
            except OSError:pass
        pending.append(str(src))
manifest.append({'enabled_backup':str(backup/'enabled.txt'),'legacy_locked_files':pending,'legacy_relocated_outside_mod':relocated,'loaded_previous_dll_relocated':loaded_relocated,'non_pyro_modules_preserved':True})
if oldmod.exists() and not any(oldmod.iterdir()):
    assert oldmod.resolve().is_relative_to((game/'ModCarrerMode/mods').resolve())
    oldmod.rmdir()
(study/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'canonical_module':'stadium_pyrotechnics.dll','archived_legacy_files':len(legacy)-len(pending),'locked_legacy_files':pending,'backup':str(backup)},indent=2))
