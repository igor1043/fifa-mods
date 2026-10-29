"""Install loose UI/assets with a file manifest and reversible backups."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sys
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--game',required=True);p.add_argument('--output',required=True);p.add_argument('--rollback',action='store_true');p.add_argument('--native-refresh',action='store_true');a=p.parse_args();game=Path(a.game).resolve();out=Path(a.output).resolve();manifest=out/'installation.json';repo=Path(__file__).resolve().parents[4]
 if a.native_refresh:
  import psutil
  if any(p.info['name'].casefold() in ('fifa16.exe','server16.exe','server16python.exe') for p in psutil.process_iter(['name']) if p.info['name']):raise ValueError('Feche FIFA e Server16 para substituir a DLL de navegação em uso')
 if a.rollback:
  data=json.loads(manifest.read_text(encoding='utf8'))
  for r in reversed(data['files']):
   target=Path(r['target']).resolve()
   if not (target.is_relative_to(game) or target.is_relative_to(repo)):raise ValueError('Destino fora da instalação')
   if target.exists() and sha(target)!=r['after']:raise ValueError('Arquivo mudou desde a instalação: '+str(target))
   if r['backup']:shutil.copy2(r['backup'],target)
   elif target.exists():target.unlink()
  print('Rollback aplicado aos arquivos do manifesto.');return
 if manifest.exists():raise ValueError('Manifesto já existe; preserve esta instalação ou faça rollback antes de reinstalar')
 env=repo/'ModCarrerMode/source/club_environment';sys.path[:0]=[str(env/'manager_market'),str(env/'market')];from package import stage
 stage(game,out/'package-game');files=[]
 def copy(source,target,scope):
  source,target=Path(source),Path(target);target.parent.mkdir(parents=True,exist_ok=True);before=sha(target) if target.exists() else None;backup=None
  if before is not None:
   backup=out/'installed-before'/scope/target.relative_to(game if scope=='game' else repo);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
  blob=source.read_bytes();temp=target.with_name(target.name+'.manager-new');temp.write_bytes(blob);os.replace(temp,target)
  files.append(dict(target=str(target),before=before,after=sha(target),backup=str(backup) if backup else None,bytes=len(blob)))
 protected=[game/'data/db/fifa_ng_db.db',game/'data/db/fifa_ng_db-meta.xml'];protected_before={str(x):sha(x) for x in protected}
 source_files=list((env/'manager_market').glob('*.py'))+[env/'manager_market/README.md',env/'market/companion.py',env/'market/native_screen.py',env/'prepared_views.py',env/'preview/prepare.py',repo/'ModCarrerMode/source/server16_py/club_environment.py']
 if a.native_refresh:source_files+=[repo/'ModCarrerMode/source/career_native/src/host/career_prepared_views.inc',repo/'ModCarrerMode/source/career_native/tests/providers/test_prepared_views.c',repo/'dinput8.dll']
 source_files+=list((repo/'ModCarrerMode/data/manager_market').rglob('*'))
 for source in source_files:
  if source.is_file():copy(source,game/source.relative_to(repo),'game')
 for scope,root,folder in (('game',game,out/'package-game'),('development',repo,out/'package')):
  for source in folder.rglob('*'):
   if source.is_file():copy(source,root/source.relative_to(folder),'game' if scope=='game' else 'development')
 # The game-specific staged NAV folder contains no BIG; publish the same waiting
 # package in both roots. The live helper replaces it after validating a career.
 placeholder=out/'package/data/ui/game/screens/career/server16/managermarket.big';target=game/'data/ui/game/screens/career/server16/managermarket.big'
 if not any(r['target']==str(target) for r in files):copy(placeholder,target,'game')
 protected_after={str(x):sha(x) for x in protected}
 if protected_after!=protected_before:raise RuntimeError('Arquivo protegido mudou durante a instalação')
 manifest.write_text(json.dumps(dict(schema=1,game=str(game),development=str(repo),files=files,protected=protected_after),ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(dict(installed=True,file_count=len(files),manifest=str(manifest),fifa_database_unchanged=True),ensure_ascii=False))

if __name__=='__main__':main()
