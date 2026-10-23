import portable_paths as portable
"""Local test helper: prepare read-only lineup assets when the career changes."""
from pathlib import Path
import json,time,hashlib,shutil,os,sys,struct
from projection import GAME,project
from build_preview import HERE,build,PAGE
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
import psutil

DEST=GAME/'data/ui/game/screens/career/server16/matchpreview.big'
LOG=HERE/'runtime/prepare.log';STATUS=HERE/'runtime/prepare.json'

def note(event,**values):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('a',encoding='utf8') as f:f.write(json.dumps({'at':time.strftime('%Y-%m-%d %H:%M:%S'),'event':event,**values},ensure_ascii=False)+'\n')

def current_state(pid):
    m=Memory();m.process_id=pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,pid)
    if not m.process_handle:return None,0
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
        return page,today
    finally:m.close()

def once():
    payload=project()
    if current_state(payload['pid'])[0]==PAGE:raise RuntimeError('Preview open; wait for Central before rebuilding')
    (HERE/'lineups.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    package=build(payload);sha=hashlib.sha256(package.read_bytes()).hexdigest()
    if not DEST.exists() or hashlib.sha256(DEST.read_bytes()).hexdigest()!=sha:
        target=DEST.with_name(DEST.name+'.s16-new');shutil.copy2(package,target);target.replace(DEST)
    state={'revision':7,'ready':True,'pid':payload['pid'],'club':payload['user']['team_id'],'opponent':payload['opponent']['team_id'],'fixture':payload['fixture'][0],'date':payload['date'],'sha256':sha,'read_only':True,'pages':3,'pagination':'FIFA arrows + one lime dot, flush to card bottom/right','initial_lineups':'native APT placements from validated save','history':'native opponent crests and per-fixture competition names/icons','footer_clearance':50}
    STATUS.parent.mkdir(parents=True,exist_ok=True);STATUS.write_text(json.dumps(state,indent=2),encoding='utf8');note('prepared',**state)
    # Keep the ownership manifest accurate without changing any other asset.
    path=HERE/'installation.json'
    if path.exists():
        manifest=json.loads(path.read_text());record=next(r for r in manifest['files'] if r['path']=='data/ui/game/screens/career/server16/matchpreview.big');record.update(sha256=sha,bytes=DEST.stat().st_size);path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return payload

def main():
    if '--watch' not in sys.argv:once();return
    lock=HERE/'runtime/prepare.lock';lock.parent.mkdir(parents=True,exist_ok=True)
    try:
        if lock.exists():
            previous=int(lock.read_text())
            if psutil.pid_exists(previous) and str(HERE).casefold() in ' '.join(psutil.Process(previous).cmdline()).casefold():raise RuntimeError('Helper already running')
        lock.write_text(str(os.getpid()))
        last=None;last_error=None;session=None
        while not (HERE/'runtime/STOP').exists():
            try:
                snapshot=GAME/'ModCarrerMode/runtime/career_fce_snapshot.json';data=json.loads(snapshot.read_text(encoding='utf8'));save=Path(data['savePath']);stat=save.stat()
                page,today=current_state(data['pid'])
                # Snapshot generation is a polling counter, not a content change.
                # Rebuild only for a different save, club, day or fixture/result.
                fixture_stamp=tuple(tuple(r[:11]) for r in data['fixtures'] if data['club'] in r[5:7])
                signature=(data['pid'],data['processCreated100ns'],data['club'],today,stat.st_mtime_ns,stat.st_size,fixture_stamp)
                if session!=data['pid']:
                    LOG.write_text('',encoding='utf8');session=data['pid'];note('session',pid=session)
                if signature!=last and psutil.pid_exists(data['pid']):
                    once();last=signature;last_error=None
            except Exception as error:
                message=str(error)
                if message!=last_error:note('waiting',error=message);last_error=message
            time.sleep(2)
    finally:
        if lock.exists() and lock.read_text()==str(os.getpid()):lock.unlink()

if __name__=='__main__':main()
