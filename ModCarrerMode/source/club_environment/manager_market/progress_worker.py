"""Small native progress view in an isolated process; never blocks simulation."""
from pathlib import Path
import hashlib,json,os,sys,time
import psutil,portable_paths as portable,prepared_views
sys.path.insert(0,str(portable.SOURCES/'market'))
from worker_market import observe,atomic
from worker import attach,io_event
from loading_progress import build,scope,view_lock,payload
from live_payload import publish as publish_data

def main():
 game=portable.GAME;root=game/'ModCarrerMode/runtime/manager_market';state=root/'progress.json'
 process=portable.session_process();created=process.create_time();memory=attach(process);last=None;last_at=0;last_owner=None;error=None
 try:
  owner_pid=int(os.environ.get('SERVER16_MANAGER_PROGRESS_OWNER','0'))
  while process.is_running() and process.create_time()==created and (not owner_pid or psutil.pid_exists(owner_pid)):
   try:
    raw=state.read_bytes();value=json.loads(raw);observed=observe(memory);owner=scope(observed,io_event(observed['save']))
    if not value.get('active') or value.get('scope')!=owner:
     time.sleep(.3);continue
    stage=value['stage'];elapsed=max(0,round(time.monotonic()-value['started_ms']/1000))
    # The mounted screen consumes tiny data-only child movies. Its native
    # lifecycle/input/footer do not restart for counters or stage changes.
    identity=(owner,stage,json.dumps(value.get('detail'),sort_keys=True),value.get('error'))
    if identity!=last and (last is None or time.monotonic()-last_at>=.7):
     publish_data(game,root,'managerprogress',payload(owner,stage,elapsed,value.get('detail'),value.get('error')))
     if owner!=last_owner:
      temporary=root/('progress-'+str(os.getpid())+'.big');build(game,temporary,stage,elapsed,value.get('detail'),value.get('error'),owner=owner)
      with view_lock(process.pid):
       latest=observe(memory);updated=json.loads(state.read_bytes())
       if not updated.get('active') or updated.get('scope')!=owner or scope(latest,io_event(latest['save']))!=owner:continue
       blob=temporary.read_bytes();atomic(game/'data/ui/game/screens/career/server16/managermarket.big',blob)
       prepared_views.publish(root/'view_ready.tsv',latest['save'],latest['profile'],latest['date'],hashlib.sha256(blob).hexdigest())
       last_owner=owner
     last=identity;last_at=time.monotonic()
     (root/'progress-status.json').write_text(json.dumps(dict(scope=owner,stage=stage,elapsed=elapsed,live_payload=True,screen_reloaded=False)),encoding='utf8')
    elif time.monotonic()-last_at>=2:
     with view_lock(process.pid):
      if state.read_bytes()==raw:
       target=game/'data/ui/game/screens/career/server16/managermarket.big'
       prepared_views.publish(root/'view_ready.tsv',observed['save'],observed['profile'],observed['date'],hashlib.sha256(target.read_bytes()).hexdigest())
       last_at=time.monotonic()
   except (OSError,ValueError,KeyError,RuntimeError) as exc:
    if str(exc)!=error:print('PROGRESS_WAIT',str(exc),flush=True);error=str(exc)
   time.sleep(.3)
 finally:memory.close()

if __name__=='__main__':main()
