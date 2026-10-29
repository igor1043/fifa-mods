"""Publish coach metadata and the selected club's own native SLC actor."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile,time,struct
import portable_paths
from lineup_worker import observe,request,publish,atomic
from coach_data import project,tsv,attach_market
from manager_market.club_profile import read as read_market_profile
from character_lighting import ensure
from player_animation import bake
from native_assets import convert
from server16_py.career_context import competition_session
from season_stats import current as season_current

def refresh_key(game):
 try:return hashlib.sha256((Path(game)/'ModCarrerMode/runtime/manager_market/state_ready.json').read_bytes()).hexdigest()
 except OSError:return 'waiting'

def generate(game,folder,req,memory,exporter,projection_cache):
 saved,context=observe(memory,game);stamp=(saved['size'],saved['mtime_ns'])
 profile=competition_session(memory,True);snapshot=season_current(game,memory,saved,profile)
 data=project(game,Path(saved['path']),req['club'],projection_cache,snapshot)
 market=read_market_profile(game,saved,profile,snapshot['date'],req['club'],data['save_hash']) if snapshot and data.get('save_hash') else None
 attach_market(data,market,snapshot,game)
 def current():
  after,ctx=observe(memory,game)
  return request(folder/'request.tsv',req['pid'])==req and after['path'].casefold()==saved['path'].casefold() and (after['size'],after['mtime_ns'])==stamp and ctx==context
 if not current():return False
 blob=tsv(data);atomic(folder/'coach.tsv',blob);revision=hashlib.sha256(blob).hexdigest()
 def ready(**values):publish(folder,req,'ready',kind='coach',profile_revision=revision,**values)
 tool=game/'ModCarrerMode/tools/club_browser/generate_lineup.exe';clip=game/'ModCarrerMode/data/club_browser/animations/coach_crossed.json'
 # A dedicated coach fixture contains only real club ID/colors; no player.
 fixture=data['fixture']
 if not tool.is_file() or not clip.is_file():
  ready(actor=0,message='O renderizador do técnico não está instalado.',career=context[2]);return True
 model_identity=f'coach-native-v1/{req["club"]}/{tool.stat().st_size}/{tool.stat().st_mtime_ns}'.encode()+clip.read_bytes()+fixture
 for suffix in ('.rx3','_textures.rx3'):
  asset=f'data/sceneassets/slc/specificmanager_{req["club"]}_0_0{suffix}'
  try:raw=portable_paths.read_asset(asset)
  except (OSError,ValueError):raw=b''
  if not raw:
   if current():ready(actor=0,message='O modelo 3D deste técnico não está instalado.',career=context[2])
   return True
  model_identity+=hashlib.sha256(raw).digest()
 identity=hashlib.sha256(model_identity).hexdigest();cache=game/'ModCarrerMode/cache/club_browser/coach'/identity;target=game/'data/sceneassets/server16_club_xi'/str(req['pid'])/identity
 ensure(game,portable_paths.read_asset)
 try:
  if not (cache/'assets.json').is_file():
   with tempfile.TemporaryDirectory(prefix='coach-',dir=folder) as temp:
    temp=Path(temp);source=temp/'coach.bin';source.write_bytes(fixture);model=temp/'coach.ff3d'
    transcript=exporter.run(tool,game,source,model,timeout=45,pose=402);atomic(folder/'coach-export.log',transcript.encode('utf8'))
    if not current():return False
    if model.read_bytes()[:8]==b'FF3D0003':bake(model,clip,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',cancel=lambda:not current())
    else:convert(model,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',animated=True)
    cache.parent.mkdir(parents=True,exist_ok=True);os.replace(temp/'native',cache)
  if not current():return False
  if not (target/'assets.json').is_file():
   target.parent.mkdir(parents=True,exist_ok=True)
   with tempfile.TemporaryDirectory(prefix='coach-publish-',dir=target.parent) as temp:
    out=Path(temp)/'native';out.mkdir()
    for p in cache.iterdir():
     try:os.link(p,out/p.name)
     except OSError:shutil.copy2(p,out/p.name)
    os.replace(out,target)
  if not current():return False
  assets=json.loads((target/'assets.json').read_text());height=round(assets['bounds'][4]-assets['bounds'][1]);ready(actor=1,player=100000000+req['club'],height=height,animated=int((target/'animation.bin').is_file()),hash=identity,pages=assets['pages'],bindings=','.join(str(row[0]) for row in assets['bindings']),renderer='native',career=context[2]);return True
 except InterruptedError:raise
 except (ValueError,OSError,RuntimeError) as error:
  atomic(folder/'coach-error.log',repr(error).encode('utf8'))
  if current():ready(actor=0,message='Modelo deste técnico indisponível. Os dados do clube continuam disponíveis.',career=context[2])
  return True
