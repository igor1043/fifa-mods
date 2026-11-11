"""Observe completed native save events and restore this career's user appearance."""
from pathlib import Path
import json,os,struct,sys,time,sqlite3
import psutil
import portable_paths
from preview_files import atomic,read_bytes
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
from server16_py.career_active_save import process_created
import manager_appearance as appearance
from manager_market.model_assets import catalog,installed


def main():
    pid=int(sys.argv[sys.argv.index('--pid')+1]);game=portable_paths.GAME
    try:process=psutil.Process(pid);created=process.create_time();executable=process.exe()
    except (psutil.NoSuchProcess,psutil.AccessDenied):return
    if Path(executable).resolve()!=game/'fifa16.exe':return
    memory=Memory();memory.process_id=pid;memory.process_handle=memory.kernel32.OpenProcess(0x410,False,pid)
    if not memory.process_handle:return
    try:memory.base_module=memory._get_base_address(executable);born=process_created(memory)
    except OSError:memory.close();return
    root=game/'ModCarrerMode/runtime/user_manager';root.mkdir(parents=True,exist_ok=True)
    choices={key:row for key,row in catalog(game).items() if installed(game,row)};allowed={key:row['assetId'] for key,row in choices.items()}
    last_event=None;current=None;publication=None;bound_draft=None;owner_path=None;last_error=None
    try:
        while process.is_running() and process.create_time()==created:
            try:
                scope=competition_session(memory,True)
                if not isinstance(scope,dict) or scope.get('career_role')!=1:
                    if publication is not None:
                        atomic(root/'models_ready.tsv',b'');atomic(root/'active.json',b'{}');publication=None
                    current=None;owner_path=None;last_event=None
                    time.sleep(.5);continue
                records=[]
                for name in ('career_save_source.tsv','career_active_save.tsv'):
                    try:
                        e=dict(line.split('=',1) for line in read_bytes(game/'ModCarrerMode/runtime'/name).decode('utf-8-sig').splitlines() if '=' in line)
                        if int(e.get('schema',0))==3 and int(e['pid'])==pid and int(e['process_created_100ns'])==born and e['save_type']=='SaveType_Career' and e['complete_file']=='1' and e['operation'] in ('read','write'):
                            records.append((int(e['access_tick_ms']),e))
                    except (OSError,ValueError,KeyError,UnicodeError):continue
                if not records:time.sleep(.5);continue
                tick,event=max(records,key=lambda pair:pair[0]);save=Path(event['path']);signature=(tick,event['operation'],str(save).casefold())
                if save.name.upper()!='DATA' or not (save.parent/'INDEX').is_file():raise ValueError('Native save path unavailable')
                if signature!=last_event:
                    if save.stat().st_size!=int(event['size_bytes']):raise InterruptedError('Save still changing')
                    with save.open('rb') as stream:header=stream.read(160)
                    if len(header)!=160 or header[116:132]!=b'SaveType_Career\0':raise ValueError('Not a career save')
                    digest=appearance.snapshot(save);loaded=appearance.load_record(save,digest)
                    if loaded and loaded['asset']>0 and allowed.get(loaded['coach'])!=loaded['asset']:loaded=None
                    if event['operation']=='read':current=loaded
                    else:
                        try:draft=dict(line.split('=',1) for line in read_bytes(root/'draft.tsv').decode('utf8').splitlines() if '=' in line)
                        except (OSError,UnicodeError):draft={}
                        armed=(draft.get('pid')==str(pid) and draft.get('created')==str(born) and draft.get('phase')=='initializing' and 0<int(draft.get('armed_tick','0'))<tick and draft.get('nonce')!=bound_draft)
                        chosen=appearance.selected(draft,pid=pid,created=born,event_tick=tick,operation=event['operation'],allowed=allowed)
                        if armed:
                            current=chosen or dict(coach='',asset=0);bound_draft=draft.get('nonce')
                            draft['phase']='bound';atomic(root/'draft.tsv',(''.join(k+'='+str(v)+'\n' for k,v in draft.items())).encode('utf8'))
                        elif current is None:current=loaded
                        if current is not None:appearance.save(save,digest,current if current['asset']>0 else None,scope['club_id'],tick)
                    owner_path=str(save).casefold();last_event=signature
                if owner_path!=str(save).casefold():time.sleep(.5);continue
                state=dict(pid=pid,created=born,context=scope['context_address'],epoch=scope['context_epoch'],club=scope['club_id'],date=0,
                           operation=event['operation'],access_tick_ms=tick,path=event['path'],branch='user-manager',digest=digest,revision=digest,schema=2)
                # The native bridge validates the exact live calendar day too.
                code=memory.read_process_memory(memory.base_module+0x44563f0,24)
                if code[7:9]!=b'\xc7\x01':raise ValueError('Calendar descriptor changed')
                index=struct.unpack_from('<I',code,9)[0]
                if index>4096:raise ValueError('Calendar service out of bounds')
                wrapper=memory.read_int64(scope['registry_address']+index*32+24);calendar=memory.read_int64(wrapper)
                day,month,year=struct.unpack('<3i',memory.read_process_memory(calendar+0x34,12))
                if not 1<=day<=31 or not 1<=month<=12 or not 2000<=year<=2200:raise ValueError('Calendar unavailable')
                state['date']=year*10000+month*100+day
                key=(tuple(state.items()),tuple(current.items()) if current else ())
                if key!=publication:
                    lines=['S16MGR2']+[str(k)+'='+str(v) for k,v in state.items()]
                    if current is not None:lines.append(f'row={state["club"]}|{current["asset"]}')
                    if current and current['asset']>0:
                        atomic(root/'active.json',json.dumps(dict(state,**current)).encode('utf8'))
                    else:atomic(root/'active.json',b'{}')
                    atomic(root/'models_ready.tsv',('\n'.join(lines)+'\n').encode('utf8'));publication=key;last_error=None
            except (OSError,ValueError,KeyError,InterruptedError,sqlite3.Error) as error:
                message=(type(error).__name__,str(error)[:160])
                if message!=last_error:print('APPEARANCE_WAIT',*message,flush=True);last_error=message
            time.sleep(.5)
    except psutil.NoSuchProcess:pass
    finally:memory.close()


if __name__=='__main__':main()
