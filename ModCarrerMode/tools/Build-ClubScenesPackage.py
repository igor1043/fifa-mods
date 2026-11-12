"""Extraction-only update for an existing FIFA Friends V12 installation."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,tempfile,zipfile

def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def build(root,output):
 root=Path(root).resolve();output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True);files={}
 def add(path):
  path=Path(path);name=path.relative_to(root).as_posix()
  if not path.is_file():raise FileNotFoundError(path)
  if path.suffix.lower() in ('.log','.sqlite3','.sqlite','.db','.dmp','.pyc','.pdb','.zip') or '__pycache__' in path.parts:return
  if '/runtime/' in '/'+name and name not in ('ModCarrerMode/data/club_environment/room/runtime/medical_room_r57.json','ModCarrerMode/data/club_environment/room/runtime/room_roles_r57.json'):return
  if '/v3-settings/' in name or '/docs/' in name.lower():return
  files[name]=path
 def tree(relative,code=False):
  for p in (root/relative).rglob('*'):
   if not p.is_file():continue
   if code and (p.name.startswith('test_') or any(s in ('build','package','runtime','tests','dist') for s in p.relative_to(root/relative).parts)):continue
   if code and p.suffix.lower() not in ('.py','.big','.json','.ini','.xml','.nav','.png','.dds','.bin','.ico'):continue
   add(p)
 for name in ('Server16Python.exe','dinput8.dll','winmm.dll','ModCarrerMode/mods/mod_host.dll','ModCarrerMode/mods/enabled.txt','ModCarrerMode/config/loader.ini'):
  if (root/name).exists():add(root/name)
 # Enabled modules target the same installed V12 base. Existing stadium,
 # kit and scoreboard libraries remain in place in the recipient's game.
 for p in (root/'ModCarrerMode/mods').rglob('*.dll'):add(p)
 for folder in ('club_environment','club_browser','server16_py','native_mods/scoreboard_settings','native_mods/frontend_stadium'):
  tree('ModCarrerMode/source/'+folder,True)
 for p in (root/'ModCarrerMode/source').glob('*.py'):add(p)
 tree('ModCarrerMode/data')
 # Curated static dependencies avoid sharing generated player plaques and
 # career textures. Additional immutable model packs are explicit.
 asset_manifest=root/'ModCarrerMode/source/club_environment/assets-manifest.json'
 for row in json.loads(asset_manifest.read_text(encoding='utf8'))['files']:add(root/row['path'])
 for name in ('medical_department','pes_office','office_neutral','office_refresh','rehab_equipment','annex_signage'):
  tree('data/sceneassets/server16_dressing_room_v3/'+name)
 trophy=root/'data/sceneassets/server16_trophy_room'
 for p in trophy.rglob('*'):
  if p.is_file() and not any(part in ('appearance','thumbnails') or part.isdigit() for part in p.relative_to(trophy).parts[:-1]):add(p)
 if (root/'data/sceneassets/trophy').exists():tree('data/sceneassets/trophy')
 for folder in ('data/ui/nav/careermode','data/ui/game/screens/career/server16'):tree(folder)
 for name in ('data/ui/layout/careermanagerhubcfg.xml','data/ui/game/screens/fluxhub/fluxhub.big','data/ui/game/screens/settings/gamesettings.big','data/ui/game/components/careercomponents/careerhubwidget.big'):
  add(root/name)
 for name in ('data/ui/imgAssets/tiles/careerHub/server16_trophy_room.dds','data/ui/imgAssets/tileicons/ti_teamsjam_small_active.dds'):add(root/name)
 stage=Path(tempfile.mkdtemp(prefix='FIFA Friends pacote unido '))
 for name,p in files.items():
  target=stage/name;target.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(p,target)
  except OSError:shutil.copy2(p,target)
 env=dict(os.environ,PYINSTALLER_RESET_ENVIRONMENT='1')
 result=subprocess.run([str(stage/'Server16Python.exe'),'--club-environment-check','--game-root',str(stage)],cwd=stage,env=env,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0,'Bundled helper check failed'
 check=json.loads((stage/'ModCarrerMode/runtime/club_environment/check.json').read_text(encoding='utf8'));assert check['ready']
 # Build neutral first-launch screens from the actual shipped helper code.
 code="""import os,sys
from pathlib import Path
game=Path(sys.argv[1]);source=game/'ModCarrerMode/source';base=source/'club_environment';runtime=game/'ModCarrerMode/runtime/club_environment'
os.environ['SERVER16_GAME_ROOT']=str(game)
sys.path[:0]=[str(source),str(base),str(base/'vendor'),*(str(runtime/g) for g in ('room','bank','preview')),str(source/'club_browser')]
from bootstrap_ui import generate
generate()
from trophy_room.build_screen import screen,BIG
screen(game,game/BIG)
"""
 # Unlink only these stage-local hard links before regeneration, preserving
 # the original game movie files and its current career presentation.
 neutral=['bankloansv2','matchpreview','matchpreviewloading','transfermarketloading','clubfinance','dressingroom','trophyroom']
 for name in neutral:
  p=stage/f'data/ui/game/screens/career/server16/{name}.big'
  if p.exists():p.unlink()
 result=subprocess.run([os.sys.executable,'-B','-c',code,str(stage)],cwd=stage,env=env,timeout=120,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if result.returncode:raise RuntimeError(result.stderr.decode('utf8',errors='replace')[-4000:])
 for name in neutral:
  relative=f'data/ui/game/screens/career/server16/{name}.big';files[relative]=stage/relative
 clinic=json.loads((stage/'data/sceneassets/server16_dressing_room_v3/medical_department/clinic.json').read_text(encoding='utf8'))
 assert all(name in files for name in clinic['required']),'Incomplete medical model pack'
 records=[dict(path=name,bytes=p.stat().st_size,sha256=digest(p)) for name,p in sorted(files.items())]
 manifest=dict(schema=1,base='FIFA Friends V12 installed',server='0.2.30',layout='extract into the folder containing fifa16.exe',bundledRuntimeVerified=True,neutralScreens=True,files=records)
 temporary=output.with_suffix('.zip.new')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
  for i,(name,p) in enumerate(sorted(files.items())):
   z.write(p,name)
   if i%200==0:print(f'Packaged {i+1}/{len(files)}',flush=True)
  z.write(root/'ModCarrerMode/data/trophy_room/menu-card.png','ARTE-CARD-TROFEUS.png')
  z.writestr('ModCarrerMode/data/catalogs/club-scenes-package.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8'))
  z.writestr('LEIA-ME.txt',('FIFA FRIENDS V12 - VESTIÁRIO, TROFÉUS E SERVER16 0.2.30\n\n1. Feche FIFA e Server16.\n2. Extraia este ZIP na pasta que contém fifa16.exe.\n3. Mescle as pastas e substitua os arquivos solicitados.\n4. Abra pelo Server16.\n\nStart abre as configurações visuais na carreira; F12 também funciona.\nA imagem do card está em ARTE-CARD-TROFEUS.png.\n\nPacote para a mesma base FIFA Friends V12. As bibliotecas de estádios, kits,\njogadores e placares da base continuam necessárias.\nNão contém saves, bancos pessoais, histórico de técnicos ou índices BH.\n').encode('utf8'))
 with zipfile.ZipFile(temporary) as z:
  assert z.testzip() is None
  for row in records:
   with z.open(row['path']) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256'],row['path']
 os.replace(temporary,output)
 report=dict(zip=str(output),bytes=output.stat().st_size,sha256=digest(output),files=len(records)+3,runtimeVerified=True,neutralScreens=True,stage=str(stage))
 output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False));return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();build(args.root,args.output)
