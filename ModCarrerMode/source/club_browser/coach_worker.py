"""Publish coach metadata and the selected club's own native SLC actor."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile,time,struct
import portable_paths
from lineup_worker import observe,request,publish,atomic
from coach_data import project,tsv,attach_market
from manager_market.club_profile import read as read_market_profile
from character_lighting import ensure
from player_animation import bake
from coach_animation import select as select_animation
from native_assets import convert
from server16_py.career_context import competition_session
from season_stats import current as season_current
from preview_files import publish_directory
from manager_market.model_assets import actor as market_actor,fixture as model_fixture

def refresh_key(game):
 try:return hashlib.sha256((Path(game)/'ModCarrerMode/runtime/manager_market/state_ready.json').read_bytes()).hexdigest()
 except OSError:return 'waiting'

def generate(game,folder,req,memory,exporter,projection_cache):
 began=time.perf_counter();timings={}
 saved,context=observe(memory,game);stamp=(saved['size'],saved['mtime_ns'])
 profile=competition_session(memory,True);snapshot=season_current(game,memory,saved,profile)
 if snapshot is None:raise InterruptedError('Aguardando a publicação da carreira atual')
 from career_results import live_leagues
 live=live_leagues(game,saved,profile,snapshot['date']) if snapshot else None
 market_revision=refresh_key(game)
 projection_cache.load(game,Path(saved['path']))
 market=read_market_profile(game,saved,profile,snapshot['date'],req['club'],projection_cache.save_hash)
 from manager_appearance import actor as user_actor
 selected_user=user_actor(game,req['club'],dict(profile,pid=req['pid'],created=saved['process_created_100ns'],save_path=saved['path']))
 if market is None and selected_user is None:raise InterruptedError('Aguardando o vínculo atual do técnico desta carreira')
 data=project(game,Path(saved['path']),req['club'],projection_cache,snapshot,live)
 if selected_user is None:attach_market(data,market,snapshot,game)
 else:
  from manager_market.model_assets import catalog
  data['fields']['portrait']=catalog(game)[selected_user['coachId']]['image']
 timings['profile_ms']=round((time.perf_counter()-began)*1000)
 def current():
  after,ctx=observe(memory,game)
  return refresh_key(game)==market_revision and request(folder/'request.tsv',req['pid'])==req and after['path'].casefold()==saved['path'].casefold() and (after['size'],after['mtime_ns'])==stamp and ctx==context
 if not current():return False
 blob=tsv(data);atomic(folder/'coach.tsv',blob);revision=hashlib.sha256(blob).hexdigest()
 def ready(**values):publish(folder,req,'ready',kind='coach',profile_revision=revision,**values)
 selected=selected_user or market_actor(game,market)
 if selected is None:
  ready(actor=0,message='O técnico atual não possui modelo 3D instalado.' if market else 'Aguardando a identidade do mercado desta carreira.',career=context[2]);return True
 tool=game/'ModCarrerMode/tools/club_browser/generate_lineup.exe';animation_dir=game/'ModCarrerMode/data/club_browser/animations'
 # A dedicated coach fixture contains only real club ID/colors; no player.
 fixture=model_fixture(data['fixture'],selected)
 try:clip=select_animation(folder,req,animation_dir)
 except FileNotFoundError:clip=None
 if not tool.is_file() or clip is None:
  ready(actor=0,message='O renderizador do técnico não está instalado.',career=context[2]);return True
 from coach_surface import VERSION as COACH_SURFACE_VERSION
 from native_assets import MATERIAL_REVISION
 model_hashes=b''
 for suffix in ('.rx3','_textures.rx3'):
  asset=selected['base']+suffix
  try:raw=portable_paths.read_asset(asset)
  except (OSError,ValueError):raw=b''
  if not raw:
   if current():ready(actor=0,message='O modelo 3D deste técnico não está instalado.',career=context[2])
   return True
  model_hashes+=hashlib.sha256(raw).digest()
 def identity_for(candidate):
  blob=f'coach-career-identity-v1/{COACH_SURFACE_VERSION}/{req["club"]}/{selected["coachId"]}/{candidate.name}/{tool.stat().st_size}/{tool.stat().st_mtime_ns}'.encode()+candidate.read_bytes()+fixture+model_hashes
  return hashlib.sha256(blob+MATERIAL_REVISION).hexdigest()
 cache_root=game/'ModCarrerMode/cache/club_browser/coach'
 # Prefer any already prepared native idle for this exact coach/club/assets.
 # A new request used to pick an unprepared random idle and redo conversion.
 if not (cache_root/identity_for(clip)/'assets.json').is_file():
  from coach_animation import CLIPS
  cached=[name for name in CLIPS if (animation_dir/name).is_file() and (cache_root/identity_for(animation_dir/name)/'assets.json').is_file()]
  if cached:clip=select_animation(folder,req,animation_dir,clips=tuple(cached))
 identity=identity_for(clip);cache=cache_root/identity;target=game/'data/sceneassets/server16_club_xi'/str(req['pid'])/identity
 timings['actor_cached']=(cache/'assets.json').is_file()
 ensure(game,portable_paths.read_asset)
 try:
  if not (cache/'assets.json').is_file():
   # Publish the verified profile while a cold actor export is in progress.
   # Do not emit actor=0 on a warm request: the native identity handoff asks
   # once more after 0 -> 1 and must receive that cached actor immediately.
   ready(actor=0,message='Preparando o modelo 3D do técnico...',career=context[2])
   with tempfile.TemporaryDirectory(prefix='coach-',dir=folder) as temp:
    temp=Path(temp);source=temp/'coach.bin';source.write_bytes(fixture);model=temp/'coach.ff3d'
    export_key=hashlib.sha256(fixture+model_hashes+str((tool.stat().st_size,tool.stat().st_mtime_ns)).encode()).hexdigest()
    exported=game/'ModCarrerMode/cache/club_browser/coach_exports'/export_key/'model.ff3d'
    started=time.perf_counter()
    if exported.is_file():shutil.copyfile(exported,model)
    else:
     transcript=exporter.run(tool,game,source,model,timeout=45,pose=402);atomic(folder/'coach-export.log',transcript.encode('utf8'))
     if model.read_bytes()[:8] not in (b'FF3D0001',b'FF3D0003'):raise ValueError('Modelo nativo do técnico inválido')
     atomic(exported,model.read_bytes())
    timings['export_ms']=round((time.perf_counter()-started)*1000);started=time.perf_counter()
    if not current():return False
    if model.read_bytes()[:8]==b'FF3D0003':bake(model,clip,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',cancel=lambda:not current(),hair_profile='classic')
    else:convert(model,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',animated=True,hair_profile='classic')
    timings['animation_ms']=round((time.perf_counter()-started)*1000)
    cache.parent.mkdir(parents=True,exist_ok=True);publish_directory(temp/'native',cache)
  if not current():return False
  if not (target/'assets.json').is_file():
   target.parent.mkdir(parents=True,exist_ok=True)
   with tempfile.TemporaryDirectory(prefix='coach-publish-',dir=target.parent) as temp:
    out=Path(temp)/'native';out.mkdir()
    for p in cache.iterdir():
     try:os.link(p,out/p.name)
     except OSError:shutil.copy2(p,out/p.name)
    publish_directory(out,target)
  if not current():return False
  assets=json.loads((target/'assets.json').read_text());height=round(assets['bounds'][4]-assets['bounds'][1]);ready(actor=1,player=100000000+req['club'],coach_id=selected['coachId'],height=height,animated=int((target/'animation.bin').is_file()),animation=clip.stem,hash=identity,pages=assets['pages'],bindings=','.join(str(row[0]) for row in assets['bindings']),renderer='native',career=context[2]);timings.update(total_ms=round((time.perf_counter()-began)*1000),club=req['club'],coach=selected['coachId']);atomic(folder/'coach-timings.json',json.dumps(timings).encode('utf8'));print('COACH_TIMINGS',json.dumps(timings),flush=True);return True
 except InterruptedError:raise
 except (ValueError,OSError,RuntimeError) as error:
  atomic(folder/'coach-error.log',repr(error).encode('utf8'))
  if current():ready(actor=0,message='Modelo deste técnico indisponível. Os dados do clube continuam disponíveis.',career=context[2])
  return True
