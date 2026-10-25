import portable_paths as portable
"""Local test helper: prepare read-only lineup assets when the career changes."""
from pathlib import Path
import json,time,hashlib,shutil,os,sys,struct
from projection import GAME,project,snapshot_revision
from build_preview import HERE,build,PAGE
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
import psutil
import prepared_views

DEST=GAME/'data/ui/game/screens/career/server16/matchpreview.big'
LOG=HERE/'runtime/prepare.log';STATUS=HERE/'runtime/prepare.json'

def note(event,**values):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('a',encoding='utf8') as f:f.write(json.dumps({'at':time.strftime('%Y-%m-%d %H:%M:%S'),'event':event,**values},ensure_ascii=False)+'\n')

def current_state(pid,details=False):
    m=Memory();m.process_id=pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,pid)
    if not m.process_handle:return (None,0,None) if details else (None,0)
    try:
        m.base_module=m._get_base_address(psutil.Process(pid).exe())
        offsets=json.loads(portable.OFFSETS.read_text())
        page=m.get_string(offsets['ORIPGBASE'],offsets['PG1'],128);profile=competition_session(m,True);today=0
        if isinstance(profile,dict):
            code=m.read_process_memory(m.base_module+0x44563f0,24)
            if code[7:9]!=b'\xc7\x01':raise ValueError('Calendar descriptor changed')
            index=struct.unpack_from('<I',code,9)[0]
            if not 0<=index<256:raise ValueError('Calendar registry bounds')
            calendar=m.read_int64(m.read_int64(profile['registry_address']+index*32+24));day,month,year=struct.unpack('<3i',m.read_process_memory(calendar+0x34,12));today=year*10000+month*100+day
        return (page,today,profile) if details else (page,today)
    finally:m.close()

def publish_ready(payload,sha,profile):
    saved=dict(pid=payload['pid'],process_created_100ns=payload.get('process_created_100ns',0))
    prepared_views.publish(HERE/'runtime/view_ready.tsv',saved,profile,payload['date'],sha,fixture=payload['fixture'][0])

def once():
    payload=project()
    (HERE/'lineups.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    package=build(payload);sha=hashlib.sha256(package.read_bytes()).hexdigest()
    # Asset preparation can span another calendar step or save load. Discard
    # that work rather than publish a complete, but already obsolete, view.
    _,today,profile=current_state(payload['pid'],details=True)
    latest=json.loads((GAME/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'))
    stat=Path(payload['save']).stat()
    if (not isinstance(profile,dict) or profile['context_address']!=payload['context']
            or profile['club_id']!=payload['user']['team_id'] or today!=payload['date']
            or snapshot_revision(latest)!=payload['source_revision']
            or stat.st_size!=latest['saveSize']
            or stat.st_mtime_ns//100+116444736000000000!=latest['saveWriteTime100ns']):
        raise RuntimeError('A carreira avançou durante a preparação; atualizando a próxima partida')
    if not DEST.exists() or hashlib.sha256(DEST.read_bytes()).hexdigest()!=sha:
        target=DEST.with_name(DEST.name+'.s16-new');shutil.copy2(package,target);target.replace(DEST)
    state={'revision':7,'ready':True,'pid':payload['pid'],'club':payload['user']['team_id'],'opponent':payload['opponent']['team_id'],'fixture':payload['fixture'][0],'date':payload['date'],'sha256':sha,'read_only':True,'pages':3,'pagination':'FIFA arrows + one lime dot, flush to card bottom/right','initial_lineups':'native APT placements from validated save','history':'native opponent crests and per-fixture competition names/icons','footer_clearance':50}
    STATUS.parent.mkdir(parents=True,exist_ok=True);STATUS.write_text(json.dumps(state,indent=2),encoding='utf8');note('prepared',**state)
    payload['package_sha256']=sha
    publish_ready(payload,sha,profile)
    if payload.get('context'):
        refresh=HERE/'runtime/native_refresh.tsv';temporary=refresh.with_suffix('.new')
        temporary.write_text(f"schema=2\npid={payload['pid']}\nclub={payload['user']['team_id']}\ncontext={payload['context']:x}\ndate={payload['date']}\nfixture={payload['fixture'][0]}\nrevision={sha}\n",encoding='ascii');temporary.replace(refresh)
    # Keep the ownership manifest accurate without changing any other asset.
    path=HERE/'installation.json'
    if path.exists():
        manifest=json.loads(path.read_text());record=next(r for r in manifest['files'] if r['path']=='data/ui/game/screens/career/server16/matchpreview.big');record.update(sha256=sha,bytes=DEST.stat().st_size);path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return payload

def main():
    # An isolated process prevents market builders from touching preview globals.
    companion=None;market_child=None;market_retry=0
    market_source=portable.SOURCES/'market'
    if (market_source/'companion.py').is_file():
        import importlib.util
        spec=importlib.util.spec_from_file_location('server16_market_companion',market_source/'companion.py')
        companion=importlib.util.module_from_spec(spec);spec.loader.exec_module(companion)
        if companion.dispatch(portable):return
    if '--watch' not in sys.argv:once();return
    lock=HERE/'runtime/prepare.lock';lock.parent.mkdir(parents=True,exist_ok=True)
    try:
        if lock.exists():
            previous=int(lock.read_text())
            if psutil.pid_exists(previous) and str(HERE).casefold() in ' '.join(psutil.Process(previous).cmdline()).casefold():raise RuntimeError('Helper already running')
        lock.write_text(str(os.getpid()))
        last=None;last_error=None;session=None;prepared=None
        while not (HERE/'runtime/STOP').exists():
            try:
                if companion and time.monotonic()>=market_retry and (market_child is None or market_child.poll() is not None):
                    market_retry=time.monotonic()+15
                    try:market_child=companion.launch(portable,portable.session_process().pid)
                    except Exception as error:note('market_companion_waiting',error=str(error))
                snapshot=GAME/'ModCarrerMode/runtime/career_fce_snapshot.json';data=json.loads(snapshot.read_text(encoding='utf8'));save=Path(data['savePath']);stat=save.stat()
                page,today,profile=current_state(data['pid'],details=True)
                # Snapshot generation is a polling counter, not a content change.
                # Rebuild only for a different save, club, day or fixture/result.
                signature=(snapshot_revision(data),today,stat.st_mtime_ns,stat.st_size)
                if session!=data['pid']:
                    LOG.write_text('',encoding='utf8');session=data['pid'];note('session',pid=session)
                if signature!=last and psutil.pid_exists(data['pid']):
                    prepared=once();last=signature;last_error=None
                elif prepared is not None and isinstance(profile,dict) and profile['context_address']==prepared['context'] and profile['club_id']==prepared['user']['team_id'] and today==prepared['date']:
                    publish_ready(prepared,prepared['package_sha256'],profile)
            except Exception as error:
                message=str(error)
                if message!=last_error:note('waiting',error=message);last_error=message
            time.sleep(2)
    finally:
        if market_child is not None and market_child.poll() is None:market_child.terminate()
        if lock.exists() and lock.read_text()==str(os.getpid()):lock.unlink()

if __name__=='__main__':main()
