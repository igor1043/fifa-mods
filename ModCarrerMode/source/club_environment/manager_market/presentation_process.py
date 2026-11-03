"""Keep Python artwork compilation out of the calendar/SQL interpreter."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import json,os,subprocess,sys,time,uuid
import psutil

class PresentationExecutor:
 def __init__(self,game,pid):
  self.game=Path(game);self.pid=pid;self.child=None;self.stop=Event();self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='manager-render-ipc')
  self.folder=self.game/'ModCarrerMode/runtime/manager_market/render_jobs'/str(os.getpid());self.folder.mkdir(parents=True,exist_ok=True)
 def submit(self,function,request):return self.pool.submit(self.render,request)
 def render(self,request):
  if self.stop.is_set():raise RuntimeError('Renderização encerrada')
  if self.child is None or self.child.poll() is not None:
   env=dict(os.environ)
   for key in ('SERVER16_MANAGER_MARKET_WORKER','SERVER16_MANAGER_PROGRESS_WORKER','SERVER16_TRANSFER_MARKET_WORKER','SERVER16_CLUB_BROWSER_WORKER'):env.pop(key,None)
   env.update(SERVER16_MANAGER_RENDER_WORKER='1',SERVER16_MANAGER_RENDER_OWNER=str(os.getpid()),SERVER16_MANAGER_RENDER_FOLDER=str(self.folder))
   command=[sys.executable]
   if not getattr(sys,'frozen',False):command.append(str(self.game/'ModCarrerMode/source/main.py'))
   command+=['--club-environment-worker','preview','--game-root',str(self.game),'--pid',str(self.pid)]
   with (self.folder/'service.log').open('ab') as stream:self.child=subprocess.Popen(command,cwd=self.game,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  token=uuid.uuid4().hex;target=self.folder/'request.json';temporary=target.with_suffix('.new')
  temporary.write_text(json.dumps(dict(job=token,key=request['key'],model=request['model']),ensure_ascii=False,separators=(',',':')),encoding='utf8');os.replace(temporary,target)
  result=self.folder/'result.json'
  while not self.stop.wait(.05):
   if self.child.poll() is not None:raise RuntimeError('Preparador visual terminou antes de publicar')
   try:
    value=json.loads(result.read_bytes())
    if value.get('job')!=token:continue
    if value.get('error'):raise RuntimeError(value['error'])
    return value['cached'],value['seconds']
   except (OSError,ValueError):pass
  raise RuntimeError('Renderização encerrada')
 def shutdown(self,wait=False,cancel_futures=True):
  self.stop.set()
  if self.child is not None and self.child.poll() is None:
   try:
    own=psutil.Process(self.child.pid)
    for p in reversed(own.children(recursive=True)):
     if p.name().casefold() in ('server16python.exe','python.exe','python3.exe'):p.terminate()
    own.terminate()
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  self.pool.shutdown(wait=wait,cancel_futures=cancel_futures)

def run():
 import portable_paths
 from worker import render_package,atomic,ROOT
 owner=psutil.Process(int(os.environ['SERVER16_MANAGER_RENDER_OWNER']));born=owner.create_time();game=portable_paths.session_process();game_born=game.create_time()
 folder=Path(os.environ['SERVER16_MANAGER_RENDER_FOLDER']).resolve();expected=(ROOT/'render_jobs'/str(owner.pid)).resolve()
 if folder!=expected:raise ValueError('Canal visual inválido')
 last=None
 while owner.is_running() and owner.create_time()==born and game.is_running() and game.create_time()==game_born:
  try:
   job=json.loads((folder/'request.json').read_bytes());token=job['job'];key=job['key']
   if token==last:time.sleep(.05);continue
   if len(token)!=32 or len(key)!=64 or any(c not in '0123456789abcdef' for c in token+key):raise ValueError('Pedido visual inválido')
   last=token
   try:
    cached,seconds=render_package(dict(model=job['model'],package=ROOT/'packages'/('managers_'+key+'.big')));value=dict(job=token,cached=cached,seconds=seconds)
   except Exception as error:value=dict(job=token,error=str(error))
   atomic(folder/'result.json',json.dumps(value).encode('utf8'))
  except (OSError,ValueError,KeyError):time.sleep(.05)
