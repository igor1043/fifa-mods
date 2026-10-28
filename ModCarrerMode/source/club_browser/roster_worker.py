"""New roster and single animated player jobs; never modifies the career save."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile,time,struct
import portable_paths
from lineup_worker import observe,atomic,publish,request
from roster_data import project,tsv
from player_animation import bake
from character_lighting import ensure
from season_stats import current as season_current
from server16_py.career_context import competition_session

def generate(game,folder,req,memory,exporter,projection_cache):
 began=time.perf_counter();saved,context=observe(memory,game);stamp=(saved['size'],saved['mtime_ns']);season=season_current(game,memory,saved,competition_session(memory,True)) if req['kind']=='roster' else None;data=project(game,Path(saved['path']),req['club'],projection_cache,season)
 def current():
  after,ctx=observe(memory,game)
  return request(folder/'request.tsv',req['pid'])==req and after['path'].casefold()==saved['path'].casefold() and (after['size'],after['mtime_ns'])==stamp and ctx==context
 if not current():return False
 if req['kind']=='roster':
  atomic(folder/'roster.tsv',tsv(data));publish(folder,req,'ready',kind='roster',players=len(data['players']),career=context[2]);return True
 player=next((p for p in data['players'] if p['id']==req['player']),None)
 if not player:raise ValueError('O jogador já não pertence ao elenco deste clube.')
 # Read evaluated assignments for this club only; no Lua is executed in FIFA.
 from room_live_kit_rules_r56 import read_assignments
 try:player['kit_rules']=read_assignments(memory,req['club'],2 if player['position']=='GOL' else 0,player['league'],player['kit_rules'])
 except (OSError,ValueError,TypeError,struct.error):pass
 tool=game/'ModCarrerMode/tools/club_browser/generate_lineup.exe';clip=game/'ModCarrerMode/data/club_browser/animations/idle_crossed.json'
 kit_identity=json.dumps({k:player[k] for k in ('club','league','jersey_name','number','kit_rules')},sort_keys=True,ensure_ascii=False).encode('utf8')
 identity=hashlib.sha256(player['fixture']+clip.read_bytes()+kit_identity+b'actor-native-stream-v3-native-coeff'+str((tool.stat().st_size,tool.stat().st_mtime_ns)).encode()).hexdigest()
 cache=game/'ModCarrerMode/cache/club_browser/player/prepared'/identity;target=game/'data/sceneassets/server16_club_xi'/str(req['pid'])/identity
 ensure(game,portable_paths.read_asset)
 if not (cache/'assets.json').is_file():
  with tempfile.TemporaryDirectory(prefix='player-',dir=folder) as temp:
   temp=Path(temp);fixture=temp/'player.bin';fixture.write_bytes(player['fixture']);model=temp/'player.ff3d';exporter.run(tool,game,fixture,model,timeout=45,pose=401)
   if not current():return False
   bake(model,clip,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',cancel=lambda:request(folder/'request.tsv',req['pid'])!=req,player=player)
   if not current():return False
   cache.parent.mkdir(parents=True,exist_ok=True);os.replace(temp/'native',cache)
 if not (target/'assets.json').is_file():
  target.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='player-publish-',dir=target.parent) as temp:
   out=Path(temp)/'native';out.mkdir()
   for p in cache.iterdir():
    try:os.link(p,out/p.name)
    except OSError:shutil.copy2(p,out/p.name)
   os.replace(out,target)
 if not current():return False
 assets=json.loads((target/'assets.json').read_text());bindings=','.join(str(row[0]) for row in assets['bindings'])
 atomic(folder/'player-timings.json',json.dumps(dict(club=req['club'],player=req['player'],seconds=round(time.perf_counter()-began,3),frames=assets['animation_frames']),indent=2).encode())
 publish(folder,req,'ready',kind='player',player=req['player'],players=1,hash=identity,pages=assets['pages'],bindings=bindings,renderer='native',career=context[2]);return True
