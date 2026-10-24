"""Read-only market companion. Uses the shipped runtime, no injection or SQL writes.

The calendar, completed deals, current players and memberships come from the
verified native owner-thread snapshot. Disk supplies the immutable catalogue.
"""
from pathlib import Path
import hashlib,json,os,struct,sys,time
import psutil
import portable_paths as portable
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
from server16_py.career_active_save import read_active_save
from read_market import read_snapshot
from review_assets import export_assets
from layout import make_scenes,Scene,shell
from native_screen import build,PAGE
from live_market import read_live

GAME=portable.GAME
ROOT=GAME/'ModCarrerMode/runtime/club_environment/market'
DEST=GAME/'data/ui/game/screens/career/server16/transfermarket.big'
_prepared=None

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+str(os.getpid())+'.new');tmp.write_bytes(data);os.replace(tmp,path)

def save_json(path,value):atomic(path,json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'))

def log(event,**values):
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'worker.log').open('a',encoding='utf8') as stream:stream.write(json.dumps(dict(at=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**values),ensure_ascii=False)+'\n')

def observe(memory):
    profile=competition_session(memory,True)
    if not isinstance(profile,dict) or profile.get('career_role')!=1:raise ValueError('Aguardando carreira de treinador.')
    save=read_active_save(GAME,memory)
    code=memory.read_process_memory(memory.base_module+0x44563f0,24)
    if code[7:9]!=b'\xc7\x01':raise ValueError('Descritor do calendário incompatível.')
    index=struct.unpack_from('<I',code,9)[0]
    if not 0<=index<256:raise ValueError('Índice de calendário fora dos limites.')
    calendar=memory.read_int64(memory.read_int64(profile['registry_address']+index*32+24))
    day,month,year=struct.unpack('<3i',memory.read_process_memory(calendar+0x34,12))
    from datetime import date
    date(year,month,day);today=year*10000+month*100+day
    signature=(save['pid'],save['process_created_100ns'],save['path'].casefold(),save['size'],save['mtime_ns'],profile['context_address'],profile['club_id'],today)
    return dict(save=save,profile=profile,date=today,signature=signature)

def placeholder(message='Aguardando os dados da carreira.'):
    s=Scene('overview','Mercado de Transferências');s.rect(0,0,1920,1080,'#034067');s.rect(60,90,1800,828,'#f4f6f7')
    s.text(100,128,1700,70,'MERCADO DE TRANSFERÊNCIAS',40)
    s.text(100,360,1700,60,message,29)
    s.text(100,450,1700,60,'Os dados serão exibidos automaticamente.',25)
    s.action(100,700,320,58,'Voltar','leave');scene=s.pack();scene.update(back='overview',ready=False,automatic=True,entryToken='waiting')
    # Keep every tab target defined while data is unavailable, so input cannot
    # fall into a missing scene or navigate to another career's cached data.
    import copy
    scenes=[scene]
    for key in ('leagues','clubs','deals','mine'):
        item=copy.deepcopy(scene);item['key']=key;scenes.append(item)
    return scenes

def publish(snapshot,memory=None,live=None):
    global _prepared
    if live is None:raise ValueError('Aguardando leitura nativa do mercado em tempo real.')
    # Freshness-only publications reuse the decoded catalogue and artwork.
    # Date, save revision, club or deal changes invalidate this cache.
    key=(snapshot['signature'],live['revision'])
    if _prepared is not None and _prepared[0]==key:
        _,original,scenes,assets,art=_prepared;data=dict(original)
    else:
        data=read_snapshot(GAME,snapshot['save']['path'],club_override=snapshot['profile']['club_id'],date_override=snapshot['date'],live=live)
        scenes=[s for s in make_scenes(data) if s['key']!='entry']
        assets,art=export_assets(data,ROOT/'assets')
        _prepared=(key,dict(data),scenes,assets,art)
    data['pid']=snapshot['save']['pid'];data['userid']=snapshot['profile']['userid'];data['dataAsOf']='live-career'
    data['capturedMs']=live['capturedMs']
    token=f"{data['pid']}:{snapshot['profile']['context_epoch']}:{live['capturedMs']}"
    for scene in scenes:
        scene.update(ready=True,automatic=True,entryToken=token)
    package=ROOT/'package/transfermarket.big';build(GAME,package,scenes,assets)
    if memory is not None and observe(memory)['signature']!=snapshot['signature']:raise RuntimeError('A carreira mudou durante a preparação do mercado.')
    if memory is not None:
        import ctypes
        timer=memory.kernel32.GetTickCount64;timer.restype=ctypes.c_ulonglong
        current=read_live(ROOT/'live_market.tsv',snapshot,timer())
        if (current['entry'],current['revision'])!=(live['entry'],live['revision']):raise RuntimeError('O mercado mudou durante a preparação da tela.')
    atomic(DEST,package.read_bytes())
    save_json(ROOT/'market.json',data)
    state=dict(schema=3,ready=True,pid=data['pid'],club=data['clubId'],date=snapshot['date'],saved_date=data['savedDate'],save_hash=data['sourceHash'],signature=snapshot['signature'],deals=len(data['transfers']),bytes=package.stat().st_size,read_only=True,source='live-career',entry=live['entry'],entry_token=token,live_revision=live['revision'],captured_ms=live['capturedMs'],assets=len(art),fallbacks=sum(a['fallback'] for a in art),sha256=hashlib.sha256(package.read_bytes()).hexdigest())
    save_json(ROOT/'status.json',state);log('prepared',**state)
    return state

def publication_due(signature,captured_ms,last,last_capture,elapsed):
    return signature!=last or (captured_ms!=last_capture and elapsed>=4)

def invalidate(message='Atualizando os dados desta carreira...'):
    package=ROOT/'package/transfermarket_waiting.big';build(GAME,package,placeholder(message),{})
    atomic(DEST,package.read_bytes())
    save_json(ROOT/'status.json',dict(schema=1,ready=False,read_only=True,message=message))

def main():
    process=portable.session_process();created=process.create_time();memory=Memory();memory.process_id=process.pid
    memory.process_handle=memory.kernel32.OpenProcess(0x410,False,process.pid)
    if not memory.process_handle:raise OSError('FIFA não permite leitura.')
    memory.base_module=memory._get_base_address(process.exe())
    ROOT.mkdir(parents=True,exist_ok=True);last=None;last_capture=None;last_publish=0.;error=None
    # Lock is process-scoped, so a second supervisor never races package writes.
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.GetTickCount64.restype=ctypes.c_ulonglong
    mutex=kernel.CreateMutexW(None,False,'Local\\Server16Market_'+str(process.pid))
    if not mutex or ctypes.get_last_error()==183:
        if mutex:kernel.CloseHandle(mutex)
        memory.close();return
    try:
        log('started',pid=process.pid)
        invalidate()
        while process.is_running() and process.create_time()==created and not (ROOT/'STOP').exists():
            try:
                snapshot=observe(memory)
                live=read_live(ROOT/'live_market.tsv',snapshot,kernel.GetTickCount64())
                signature=(snapshot['signature'],live['revision'],live['entry'])
                if publication_due(signature,live['capturedMs'],last,last_capture,time.monotonic()-last_publish):
                    publish(snapshot,memory,live=live);last=signature;last_capture=live['capturedMs'];last_publish=time.monotonic()
                error=None
            except Exception as exc:
                message=str(exc)
                if message!=error:log('waiting',error=message);error=message
            time.sleep(2)
    except psutil.NoSuchProcess:pass
    finally:memory.close();kernel.CloseHandle(mutex)

if __name__=='__main__':main()
