"""Stage identity-based career assets from the accepted fixed-club models.

This explicit packaging tool never changes the FIFA installation. Give an
empty --output directory and distribute its data/ and ModCarrerMode/ folders
together. Run again after reviewing an updated baseline coach model.
"""
from pathlib import Path
import argparse,hashlib,json,shutil

def prepare(game,output):
 game=Path(game).resolve();output=Path(output).resolve()
 if output==game or game in output.parents or output.exists() and any(output.iterdir()):raise ValueError('Use an empty staging directory outside the game')
 registry=json.loads((game/'ModCarrerMode/data/manager_market/manager_models.json').read_text(encoding='utf8'))
 from model_assets import KEY
 seen=set()
 for row in registry['coaches']:
  ident=row['sourceCoachId'];club=row['baselineClubId']
  if not KEY.fullmatch(row['coachId']) or type(ident)!=int or not 1<=ident<=200000 or ident in seen or type(club)!=int or not 1<=club<=200000:raise ValueError('Invalid source identity')
  seen.add(ident);row['assetId']=ident;row['files']={}
  for weather in (0,1):
   for suffix in ('','_textures'):
    src=game/f'data/sceneassets/slc/specificmanager_{club}_0_{weather}{suffix}.rx3';raw=src.read_bytes()
    if len(raw)<32 or raw[:4] not in (b'RX3l',b'RX3b'):raise ValueError('Not a native RX3: '+str(src))
    dst=output/f'data/sceneassets/manager_market/{ident}/model_{weather}{suffix}.rx3';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);row['files'][dst.name]=hashlib.sha256(raw).hexdigest()
  for key in ('model','textures'):row.setdefault('baseline'+key.title(),row[key])
  row['model']=f'data/sceneassets/manager_market/{ident}/model_0.rx3';row['textures']=f'data/sceneassets/manager_market/{ident}/model_0_textures.rx3';row['modelSha256']=row['files']['model_0.rx3'];row['texturesSha256']=row['files']['model_0_textures.rx3']
 registry.update(schema=2,runtimeOverrideEnabled=True,deduplication='Stable coach identity assets are independent of club baseline assignments')
 dst=output/'ModCarrerMode/data/manager_market/manager_models.json';dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return len(seen)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--game',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print('Prepared coaches:',prepare(args.game,args.output))
