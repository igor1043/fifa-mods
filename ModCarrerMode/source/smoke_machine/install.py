"""Install only the new machine package; retain original files and other plugins verbatim."""
from pathlib import Path
import shutil,datetime,json,hashlib
R=Path(__file__).resolve().parent
study=Path(r'J:\mods\fifa 16\estudos fifa 16\43_SMOKE_MACHINE_20261014');study.mkdir(exist_ok=True)
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
backup=study/('backup_'+stamp);backup.mkdir()
block=(R/'smoke_machine.lua').read_bytes()
assert block.count(b'FIFA16_SMOKE_MACHINE_LUA_V1=true')==1
readme='''Maquina de fumaca / lancador de pirotecnia

Modelo FBX fornecido convertido para RX3 estatico, sem esqueleto.
Texturas de cor e normal preservadas, com mipmaps e acabamento nativo.
Altura aproximada: 55 cm, base centralizada no chao com elevacao de 2 cm.
20 maquinas: oito laterais e doze atras dos gols, cobrindo todos os pontos atuais de emissao.
As duas centrais foram substituidas por quatro a -14m/+14m; nao ha maquina no meio-campo.
Maquinas e pontos de emissao afastados mais 50 cm para fora do campo.
Malha otimizada: 3.329 triangulos por maquina, 66.580 triangulos no conjunto completo.
Uma malha e um pacote de texturas compartilhados entre as instancias.

DLL unica: smoke_machine.dll. Configuracao local: smoke_machine.ini.
Segue [match] pyrotechnics do controle do Server16 e [pyro] enabled do modulo de fogos.
Nao aparece na previa KickOffHub ou selecao de equipes; conserva a maquina durante pausa/replay da partida.
O modulo adiciona os equipamentos fisicos; disparos e cores continuam sob responsabilidade de stadium_pyrotechnics.dll.
Nao depende de clube, estadio ou competicao.

Feche e abra o FIFA para carregar a DLL e os assets novos.
Log: ModCarrerMode/logs/smoke_machine.log.
Validacoes de conversao, Lua 5.1, pontos de emissao e compilacao passaram.
A visualizacao dentro do FIFA precisa ser confirmada no jogo.
'''
package=R/'package'
mod=package/'ModCarrerMode/mods/smoke_machine';mod.mkdir(parents=True,exist_ok=True)
shutil.copy2(R/'build/smoke_machine.dll',mod/'smoke_machine.dll')
shutil.copy2(R/'smoke_machine.lua',mod/'smoke_machine.lua')
(mod/'smoke_machine.ini').write_text('[smoke_machine]\nenabled=1\nground_lift_cm=2\n',encoding='utf8')
(mod/'README.txt').write_text(readme,encoding='utf8')
manifest=[]
for root in (Path(r'U:\fifa 16'),Path(r'U:\mods\FIFA Friends V12')):
    scope=backup/('game' if root.name=='fifa 16' else 'mod');scope.mkdir()
    untouched=[root/'ModCarrerMode/config/match_presentation.ini',root/'ModCarrerMode/mods/stadium_pyrotechnics/pyro.ini',
               root/'ModCarrerMode/mods/stadium_pyrotechnics/stadium_pyrotechnics.dll',root/'ModCarrerMode/mods/entrance_props/entrance_props.dll',
               root/'ModCarrerMode/mods/var_cabin/var_cabin.dll']
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in untouched if p.exists()}
    for src in package.rglob('*'):
        if not src.is_file():continue
        rel=src.relative_to(package);dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            saved=scope/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
        if dest.name=='smoke_machine.ini' and dest.exists():continue
        shutil.copy2(src,dest);assert src.read_bytes()==dest.read_bytes()
        manifest.append({'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    lua=root/'data/fifarna/lua/assets/sle.lua';oldLua=lua.read_bytes()
    saved=scope/lua.relative_to(root);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(lua,saved)
    if b'FIFA16_SMOKE_MACHINE_LUA_V1' not in oldLua:
        newLua=oldLua+b'\r\n'+block+b'\r\n'
        assert lua.read_bytes()==oldLua,'SLE changed concurrently'
        lua.write_bytes(newLua);assert lua.read_bytes().startswith(oldLua)
    else:assert block in oldLua,'Existing machine block differs; merge required'
    enabled=root/'ModCarrerMode/mods/enabled.txt';oldEnabled=enabled.read_bytes()
    saved=scope/enabled.relative_to(root);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(enabled,saved)
    line=b'smoke_machine\\smoke_machine.dll'
    if line not in [x.strip() for x in oldEnabled.splitlines()]:
        updated=oldEnabled+(b'' if oldEnabled.endswith(b'\n') else b'\r\n')+line+b'\r\n'
        assert enabled.read_bytes()==oldEnabled,'Loader changed concurrently'
        enabled.write_bytes(updated);assert enabled.read_bytes().startswith(oldEnabled)
    assert sum(x.strip()==line for x in enabled.read_bytes().splitlines())==1
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in before.items()),'Existing pyro controls/plugin changed'
    manifest.append({'root':str(root),'existing_plugins_and_pyro_controls_unchanged':True,'sle_original_prefix_preserved':True,'loader_original_prefix_preserved':True})
for name in ('smoke_machine.cpp','smoke_machine.lua','launch_sites.h','presentation.h','prepare_native.py','export_fbx.py','convert_model.py',
             'verify.py','install.py','build.cmd','test_sites.cpp','conversion_validation.json','validation.json','smoke_machine_rx3_0.png','smoke_machine_rx3_1.png'):
    shutil.copy2(R/name,study/name)
shutil.copytree(package,study/'package',dirs_exist_ok=True)
(study/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'installed_roots':['U:\\fifa 16','U:\\mods\\FIFA Friends V12'],'module':'smoke_machine.dll','machines':20,'backup':str(backup)},indent=2))
