"""Install the existing multiball module plus converted supports, with backups."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('--assets',type=Path,required=True,help='Root containing the five model folders')
parser.add_argument('--game',type=Path,required=True)
parser.add_argument('--development',type=Path,required=True)
parser.add_argument('--backup',type=Path,required=True)
args=parser.parse_args()
processes=subprocess.run(['tasklist','/FI','IMAGENAME eq FIFA16.exe','/FO','CSV','/NH'],capture_output=True,check=True).stdout.lower()
if b'fifa16.exe' in processes:raise SystemExit('Feche o FIFA antes de instalar a DLL.')
source=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
files={}
def plan(src,dest,scope,relative):
    if src.resolve()==dest.resolve():return
    if not src.is_file():raise FileNotFoundError(src)
    files[str(dest.resolve()).lower()]=(src,dest,scope,relative)
for label,root in [('dev',args.development),('game',args.game)]:
    if not root.is_dir():raise NotADirectoryError(root)
    for variant in ('brasileirao','cbf','paulistao','generic1','generic2'):
        for name in ('model.rx3','textures.rx3'):
            relative=Path('data/sceneassets/standball')/variant/name
            plan(args.assets/variant/name,root/relative,label,relative)
    for name,src in [('multiball_visual.dll',source/'build/multiball_visual.dll'),('standball.lua',source/'standball.lua'),('standball.ini',source/'standball.ini')]:
        relative=Path('ModCarrerMode/mods/multiball_visual')/name
        if name=='standball.ini' and (root/relative).is_file():continue
        plan(src,root/relative,label,relative)
    for src in source.iterdir():
        if src.is_file():
            relative=Path('ModCarrerMode/source/multiball_visual')/src.name
            plan(src,root/relative,label,relative)
args.backup.mkdir(parents=True,exist_ok=False)
protected={}
for root in (args.game,args.development):
    for rel in ('ModCarrerMode/mods/enabled.txt','ModCarrerMode/mods/entrance_props/entrance_props.dll','ModCarrerMode/mods/var_cabin/var_cabin.dll','ModCarrerMode/mods/smoke_machine/smoke_machine.dll','ModCarrerMode/mods/stadium_pyrotechnics/stadium_pyrotechnics.dll'):
        p=root/rel
        if p.is_file():protected[p]=sha(p)
manifest=[]
for src,dest,scope,rel in files.values():
    saved=args.backup/scope/rel
    if dest.is_file():saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
    manifest.append({'source':str(src),'target':str(dest),'sha256':sha(src),'backup':str(saved) if saved.is_file() else None})
(args.backup/'plan.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
for entry in manifest:
    src,dest=Path(entry['source']),Path(entry['target'])
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    assert sha(dest)==entry['sha256'],dest
assert all(sha(p)==h for p,h in protected.items()),'Outro modulo foi alterado durante a instalacao'
(args.backup/'manifest.json').write_text(json.dumps({'installed':manifest,'existing_modules_unchanged':True},indent=2),encoding='utf8')
print(json.dumps({'installed_files':len(manifest),'roots':[str(args.game),str(args.development)],'backup':str(args.backup),'existing_modules_unchanged':True},indent=2))
