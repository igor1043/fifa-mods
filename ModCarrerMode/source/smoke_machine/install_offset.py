from pathlib import Path
import shutil,hashlib,json,datetime,re,math
R=Path(__file__).resolve().parent
P=R.parent/'stadium_pyrotechnics'
study=Path(r'J:\mods\fifa 16\estudos fifa 16\43_SMOKE_MACHINE_20261014\offset_50cm')
def sites(path):return [(float(x),float(z)) for x,z in re.findall(r'\{(-?\d+),(-?\d+),[^}]+\}',path.read_text())]
old=sites(study/'launch_sites_before.h');new=sites(R/'launch_sites.h')
assert len(old)==len(new)==18
for (x,z),(nx,nz) in zip(old,new):
    assert math.hypot(nx-x,nz-z)==50
    assert (x==nx and abs(nz)==abs(z)+50) or (z==nz and abs(nx)==abs(x)+50)
before=(study/'stadium_pyrotechnics_before.cpp').read_text()
assert before.replace('-3650.0f:3650.0f','-3700.0f:3700.0f').replace('-5850.0f:5850.0f','-5900.0f:5900.0f')==(P/'stadium_pyrotechnics.cpp').read_text()
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
backup=study/('backup_'+stamp);backup.mkdir()
manifest=[]
for index,root in enumerate((Path(r'U:\fifa 16'),Path(r'U:\mods\FIFA Friends V12'))):
    protected=[root/'ModCarrerMode/mods/enabled.txt',root/'ModCarrerMode/config/match_presentation.ini',
               root/'ModCarrerMode/mods/stadium_pyrotechnics/pyro.ini',root/'ModCarrerMode/mods/smoke_machine/smoke_machine.ini']
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
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
for src in (R/'launch_sites.h',R/'verify.py',P/'stadium_pyrotechnics.cpp',P/'prepare.py',R/'validation.json'):
    shutil.copy2(src,study/src.name)
shutil.copy2(R/'build/smoke_machine.dll',R/'package/ModCarrerMode/mods/smoke_machine/smoke_machine.dll')
(study/'offset_manifest.json').write_text(json.dumps({'offset_cm':50,'all_18_bases_shifted_outwards':True,
    'pyro_source_only_two_position_changes':True,'settings_and_loader_preserved':True,'backup':str(backup),'installed':manifest},indent=2))
print('18 bases and all emitters moved exactly 50cm outward; both DLLs installed in both roots; settings unchanged.')
