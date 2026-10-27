"""Publish the approved layout without rewriting controls, Lua or unrelated plugins."""
from pathlib import Path
import shutil,hashlib,json,datetime,re
R=Path(__file__).resolve().parent;P=R.parent/'stadium_pyrotechnics'
study=Path(r'J:\mods\fifa 16\estudos fifa 16\43_SMOKE_MACHINE_20261014\four_spread_midfield')
def sites(path):return [(float(x),float(z)) for x,z in re.findall(r'\{(-?\d+),(-?\d+),[^}]+\}',path.read_text())]
old=set(sites(study/'launch_sites_before.h'));new=set(sites(R/'launch_sites.h'))
assert old-new=={(0,-3700),(0,3700)}
assert new-old=={(-1400,-3700),(-1400,3700),(1400,-3700),(1400,3700)}
assert len(new)==20
before=(study/'stadium_pyrotechnics_before.cpp').read_text()
expected=before.replace('emitterCount=10','emitterCount=12').replace('return goalShow?8:10','return goalShow?8:12')
expected=expected.replace('if (!goalShow && i<6)','if (!goalShow && i<8)')
expected=expected.replace('matrix[12]=(float)((i/2-1)*2800);','const float sidelineX[4]={-2800,-1400,1400,2800};\n            matrix[12]=sidelineX[i/2];')
expected=expected.replace('(i/2-3)*2-1','(i/2-4)*2-1').replace('intro_six_sideline','intro_eight_sideline')
assert expected==(P/'stadium_pyrotechnics.cpp').read_text()
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
backup=study/('backup_'+stamp);backup.mkdir();manifest=[]
for index,root in enumerate((Path(r'U:\fifa 16'),Path(r'U:\mods\FIFA Friends V12'))):
    protected=[root/'ModCarrerMode/mods/enabled.txt',root/'ModCarrerMode/config/match_presentation.ini',
               root/'ModCarrerMode/mods/stadium_pyrotechnics/pyro.ini',root/'ModCarrerMode/mods/smoke_machine/smoke_machine.ini',
               root/'data/fifarna/lua/assets/sle.lua']
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.exists()}
    for folder in ('smoke_machine','stadium_pyrotechnics'):
        src=(R if folder=='smoke_machine' else P)/'build'/(folder+'.dll')
        dst=root/'ModCarrerMode/mods'/folder/(folder+'.dll')
        saved=backup/str(index)/folder/dst.name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,saved)
        try:shutil.copy2(src,dst)
        except PermissionError:
            hold=R/'historico_carregado';hold.mkdir(exist_ok=True)
            target=hold/(folder+'_'+str(index)+'_'+stamp+'.dll')
            assert target.resolve().is_relative_to(R.resolve())
            assert dst.parent.resolve()==(root/'ModCarrerMode/mods'/folder).resolve()
            dst.rename(target);shutil.copy2(src,dst)
        assert src.read_bytes()==dst.read_bytes()
        manifest.append({'path':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
    readme=root/'ModCarrerMode/mods/smoke_machine/README.txt'
    if readme.exists():
        saved=backup/str(index)/'README.txt';shutil.copy2(readme,saved)
        text=readme.read_text(encoding='utf8').replace('18 maquinas: seis laterais','20 maquinas: oito laterais')
        text=text.replace('59.922 triangulos','66.580 triangulos')
        if '14 metros' not in text:text+='\nQuatro maquinas internas laterais a -14/+14 metros; nenhuma no meio-campo. Afastamento adicional de 50 cm preservado.\n'
        readme.write_text(text,encoding='utf8')
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
for src in (R/'launch_sites.h',R/'verify.py',R/'prepare_native.py',R/'smoke_machine.cpp',P/'stadium_pyrotechnics.cpp',P/'prepare.py',P/'ending.h',R/'validation.json'):
    shutil.copy2(src,study/src.name)
shutil.copy2(R/'build/smoke_machine.dll',R/'package/ModCarrerMode/mods/smoke_machine/smoke_machine.dll')
(study/'layout_manifest.json').write_text(json.dumps({'total_machines':20,'removed':sorted(old-new),'added':sorted(new-old),
    'additional_outward_offset_cm':50,'existing_settings_lua_and_loader_preserved':True,'backup':str(backup),'installed':manifest},indent=2))
print('Four inner sideline bases installed at -14/+14m; no midfield bases; matching emitters installed in both roots.')
