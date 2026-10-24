"""Isolated, read-only native asset exporter for the selected club and active save.

The FIFA process is opened with query/read rights only. No native FIFA API is
called. The exporter runs in its own process; complete native assets are published.
"""
from pathlib import Path
import argparse,hashlib,json,os,struct,subprocess,sys,tempfile,time,shutil
import psutil
from lineup_data import project,ProjectionCache
from native_assets import convert,VERSION
from model_exporter import Exporter
from character_lighting import ensure as ensure_character_lighting
import portable_paths
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
from server16_py.career_active_save import read_active_save

def atomic(path,blob):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+str(os.getpid())+'.new');temp.write_bytes(blob);os.replace(temp,path)

def request(path,pid):
    raw=path.read_bytes()
    if len(raw)>1024:raise ValueError('Pedido inválido.')
    data=dict(line.split('=',1) for line in raw.decode('ascii').splitlines())
    result={k:int(data[k]) for k in ('schema','pid','seq','club')}
    if result['schema']!=1 or result['pid']!=pid or not 0<result['seq']<2**63 or not 0<result['club']<500000:raise ValueError('Pedido de outra sessão.')
    return result

def observe(memory,game):
    profile=competition_session(memory,True)
    if not isinstance(profile,dict) or profile.get('career_role')!=1:raise ValueError('Aguardando a carreira de treinador.')
    save=read_active_save(game,memory)
    return save,(profile['context_address'],profile['context_epoch'],profile['club_id'])

def publish(folder,req,status,**fields):
    values=dict(schema=1,pid=req['pid'],seq=req['seq'],club=req['club'],status=status,**fields)
    blob=''.join(str(k)+'='+str(v).replace('\n',' ').replace('\r',' ')+'\n' for k,v in values.items())
    atomic(folder/'status.tsv',blob.encode('utf8'))

def generate(game,folder,req,memory,asset_root=None,exporter=None,projection_cache=None):
    began=time.perf_counter();timings={}
    saved,context=observe(memory,game);save=Path(saved['path']);version=(saved['size'],saved['mtime_ns'])
    ensure_character_lighting(game,portable_paths.read_asset)
    result=project(game,save,req['club'],projection_cache);tool=game/'ModCarrerMode/tools/club_browser/generate_lineup.exe'
    timings['read_save_ms']=round((time.perf_counter()-began)*1000,1)
    if not tool.is_file():raise ValueError('Renderizador dos titulares não está instalado.')
    asset_files=[game/'data/db/fifa_ng_db.db',game/'data/db/fifa_ng_db-meta.xml',tool]
    revision=hashlib.sha256(result['fixture']+str(VERSION).encode()+str([(f.stat().st_size,f.stat().st_mtime_ns) for f in asset_files]).encode()).hexdigest()
    target=(asset_root or game/'data/sceneassets/server16_club_xi')/str(req['pid'])/revision
    cache=(asset_root or game/'ModCarrerMode/cache/club_browser/xi')/'prepared'/revision
    if not (cache/'assets.json').is_file():
        with tempfile.TemporaryDirectory(prefix='xi-',dir=folder) as temp:
            temp=Path(temp);fixture=temp/'lineup.bin';fixture.write_bytes(result['fixture']);model=temp/'model.ff3d'
            preparer=exporter or Exporter();start=time.perf_counter()
            try:transcript=preparer.run(tool,game,fixture,model)
            finally:
                if exporter is None:preparer.close()
            timings['native_models_ms']=round((time.perf_counter()-start)*1000,1)
            atomic(folder/'export.log',transcript.encode('utf8'))
            if request(folder/'request.tsv',req['pid'])!=req:return False
            start=time.perf_counter()
            material_cache=(asset_root or game/'ModCarrerMode/cache/club_browser/xi')/'materials'
            convert(model,temp/'native',portable_paths.read_asset,material_cache)
            timings['native_pack_ms']=round((time.perf_counter()-start)*1000,1)
            cache.parent.mkdir(parents=True,exist_ok=True)
            os.replace(temp/'native',cache)
        timings['cache_hit']=False
    else:timings['cache_hit']=True
    if not (target/'assets.json').is_file():
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='publish-',dir=target.parent) as temp:
            publish_to=Path(temp)/'native';publish_to.mkdir()
            for item in cache.iterdir():
                try:os.link(item,publish_to/item.name)
                except OSError:shutil.copy2(item,publish_to/item.name)
            os.replace(publish_to,target)
    assets=json.loads((target/'assets.json').read_text(encoding='utf8'))
    after,latest=observe(memory,game)
    if (after['path'].casefold()!=saved['path'].casefold() or (after['size'],after['mtime_ns'])!=version or latest!=context):raise ValueError('A carreira mudou durante a renderização. Abra o clube novamente.')
    if request(folder/'request.tsv',req['pid'])!=req:return False
    atomic(folder/'roster.json',json.dumps(dict(club=req['club'],players=result['roster'],save_hash=result['save_hash'],source='active-career-save'),ensure_ascii=False,indent=2).encode('utf8'))
    pages=','.join(str(pair[0]) for pair in assets['bindings'])
    timings['total_ms']=round((time.perf_counter()-began)*1000,1)
    atomic(folder/'timings.json',json.dumps(dict(club=req['club'],seq=req['seq'],**timings),indent=2).encode())
    publish(folder,req,'ready',hash=revision,pages=assets['pages'],bindings=pages,players=11,renderer='native',source='active-career-save')
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pid',type=int,required=True);parser.add_argument('--watch',action='store_true');parser.add_argument('--once',action='store_true');args=parser.parse_args()
    game=Path(os.environ['SERVER16_GAME_ROOT']).resolve();process=psutil.Process(args.pid)
    if process.name().casefold()!='fifa16.exe' or Path(process.exe()).resolve()!=game/'fifa16.exe':raise ValueError('FIFA de outra instalação.')
    created=process.create_time();folder=game/'ModCarrerMode/runtime/club_browser'/str(args.pid);folder.mkdir(parents=True,exist_ok=True)
    m=Memory();m.process_id=args.pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,args.pid)
    if not m.process_handle:raise OSError('Não foi possível ler a carreira.')
    m.base_module=m._get_base_address(process.exe());last=None;exporter=Exporter();projection_cache=ProjectionCache()
    try:
        while process.is_running() and process.create_time()==created:
            req=None
            try:
                req=request(folder/'request.tsv',args.pid)
                signature=(req['seq'],req['club'])
                if signature!=last:
                    last=signature;publish(folder,req,'loading')
                    print('REQUEST',json.dumps(req),flush=True);completed=generate(game,folder,req,m,exporter=exporter,projection_cache=projection_cache)
                    print('COMPLETE' if completed else 'SUPERSEDED',req['seq'],flush=True)
            except FileNotFoundError as error:
                if req:publish(folder,req,'error',message='Um recurso necessário para os titulares não foi encontrado.')
            except Exception as error:
                print('ERROR',repr(error),flush=True)
                if req:publish(folder,req,'error',message=str(error)[:220])
            if args.once:return
            time.sleep(.03)
    except psutil.NoSuchProcess:pass
    finally:exporter.close();m.close()

if __name__=='__main__':main()
