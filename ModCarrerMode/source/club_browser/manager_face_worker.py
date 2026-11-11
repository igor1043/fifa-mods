"""Render an installed coach during creation, without inventing an active career."""
from pathlib import Path
import hashlib,json,os,shutil,struct,tempfile,time
from functools import lru_cache
import portable_paths
from lineup_worker import request,publish
from preview_files import atomic,publish_directory,read_bytes
from manager_market.model_assets import catalog,installed
from coach_animation import CLIPS,select as select_animation
from player_animation import bake
from native_assets import convert,MATERIAL_REVISION
from coach_surface import VERSION as SURFACE_VERSION
from character_lighting import ensure


@lru_cache(maxsize=2)
def _catalog(game,signature):
    return catalog(Path(game))


@lru_cache(maxsize=48)
def _source_hash(base,signature):
    return b''.join(hashlib.sha256(portable_paths.read_asset(base+suffix)).digest()
                    for suffix in ('.rx3','_textures.rx3'))


def _prepared_clips(directory,cache_root,identity):
    return tuple(name for name in CLIPS if (directory/name).is_file()
                 and (cache_root/identity(directory/name)/'assets.json').is_file())


def generate(game,folder,req,memory,exporter):
    started=time.perf_counter();timings={}
    registry=game/'ModCarrerMode/data/manager_market/manager_registry.ini'
    try:
        stat=registry.stat();rows=_catalog(str(game), (stat.st_size,stat.st_mtime_ns))
    except OSError:rows=catalog(game)
    selected=rows.get(req['coach'])
    if not installed(game,selected) or selected['assetId']!=req['club']:raise ValueError('Modelo não consta no catálogo instalado')
    def current():
        try:
            values=dict(line.split('=',1) for line in read_bytes(game/'ModCarrerMode/runtime/user_manager/draft.tsv').decode('utf8').splitlines() if '=' in line)
            return request(folder/'request.tsv',req['pid'])==req and values.get('pid')==str(req['pid']) and values.get('active')=='1'
        except (OSError,ValueError):return False
    def ready(**fields):publish(folder,req,'ready',kind='manager_face',**fields)
    if not current():ready(actor=0,message='Visualização encerrada');return True
    animation_dir=game/'ModCarrerMode/data/club_browser/animations'
    tool=game/'ModCarrerMode/tools/club_browser/generate_lineup.exe'
    if not tool.is_file():raise ValueError('Recursos de visualização do técnico ausentes')
    clip=select_animation(folder,req,animation_dir,state_name='manager-face-animation-choice.json')
    fixture=struct.pack('<8s5I',b'FFCOACH2',req['club'],0xb9a274,0x25282b,0xffffff,selected['assetId'])
    base=f'data/sceneassets/slc/specificmanager_{selected["assetId"]}_0_0'
    try:
        signature=tuple((str(game/base)+suffix,(game/(base+suffix)).stat().st_size,(game/(base+suffix)).stat().st_mtime_ns) for suffix in ('.rx3','_textures.rx3'))
    except OSError:
        # Packed assets have no loose file fingerprint; do not retain a digest
        # across requests when its invalidation cannot be established.
        signature=(time.monotonic_ns(),)
    source_hash=_source_hash(base,signature)
    tool_stat=tool.stat();tool_version=f'{tool_stat.st_size}/{tool_stat.st_mtime_ns}'
    def identity_for(candidate):
        return hashlib.sha256(f'manager-face-v1/{SURFACE_VERSION}/{candidate.name}/{tool_version}'.encode()+fixture+source_hash+candidate.read_bytes()+MATERIAL_REVISION).hexdigest()
    cache_root=game/'ModCarrerMode/cache/club_browser/coach'
    if not (cache_root/identity_for(clip)/'assets.json').is_file():
        cached=_prepared_clips(animation_dir,cache_root,identity_for)
        if cached:clip=select_animation(folder,req,animation_dir,clips=cached,state_name='manager-face-animation-choice.json')
    identity=identity_for(clip)
    cache=cache_root/identity;target=game/'data/sceneassets/server16_club_xi'/str(req['pid'])/identity
    model_id=hashlib.sha256(f'manager-face-source-v1/{tool_version}'.encode()+fixture+source_hash).hexdigest()
    # Use the existing bounded export cache; no new uncollected directory.
    model_cache=game/'ModCarrerMode/cache/club_browser/coach_exports'/model_id/'model.ff3d'
    timings['lookup_ms']=round((time.perf_counter()-started)*1000,2)
    timings['animation_cache_hit']=(cache/'assets.json').is_file()
    ensure(game,portable_paths.read_asset)
    if not (cache/'assets.json').is_file():
        with tempfile.TemporaryDirectory(prefix='face-',dir=folder) as temp:
            temp=Path(temp);source=temp/'coach.bin';source.write_bytes(fixture);model=temp/'coach.ff3d'
            stage=time.perf_counter()
            try:
                with model_cache.open('rb') as existing:valid=existing.read(8) in (b'FF3D0003',b'FF3D0001')
            except OSError:valid=False
            timings['model_cache_hit']=valid
            if valid:model=model_cache
            else:
                transcript=exporter.run(tool,game,source,model,timeout=45,pose=402);atomic(folder/'face-export.log',transcript.encode('utf8'))
                if not current():return False
                data=model.read_bytes()
                if data[:8] not in (b'FF3D0003',b'FF3D0001'):raise ValueError('Modelo 3D incompatível')
                model_cache.parent.mkdir(parents=True,exist_ok=True);atomic(model_cache,data)
            timings['export_ms']=round((time.perf_counter()-stage)*1000,2)
            if not current():return False
            stage=time.perf_counter()
            with model.open('rb') as data:magic=data.read(8)
            if magic==b'FF3D0003':bake(model,clip,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',cancel=lambda:not current(),hair_profile='classic')
            elif magic==b'FF3D0001':convert(model,temp/'native',portable_paths.read_asset,game/'ModCarrerMode/cache/club_browser/xi/materials',animated=True,hair_profile='classic')
            else:raise ValueError('Modelo 3D incompatível')
            timings['animation_ms']=round((time.perf_counter()-stage)*1000,2)
            if not current():return False
            cache.parent.mkdir(parents=True,exist_ok=True);publish_directory(temp/'native',cache)
    if not current():return False
    if not (target/'assets.json').is_file():
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='face-publish-',dir=target.parent) as temp:
            out=Path(temp)/'native';out.mkdir()
            for file in cache.iterdir():
                try:os.link(file,out/file.name)
                except OSError:shutil.copy2(file,out/file.name)
            publish_directory(out,target)
    if not current():return False
    assets=json.loads((target/'assets.json').read_text(encoding='utf8'));height=round(assets['bounds'][4]-assets['bounds'][1])
    timings.update(total_ms=round((time.perf_counter()-started)*1000,2),asset=req['club'],sequence=req['seq'])
    # One bounded diagnostic, replaced for each completed selection.
    atomic(folder/'face-timings.json',json.dumps(timings).encode('utf8'))
    ready(actor=1,player=100000000+req['club'],coach_id=req['coach'],height=height,animated=int((target/'animation.bin').is_file()),animation=clip.stem,hash=identity,pages=assets['pages'],bindings=','.join(str(v[0]) for v in assets['bindings']),renderer='native',career=0)
    return True
