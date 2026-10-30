"""Isolated game companion. Only the manager sidecar and its UI are written."""
from pathlib import Path
import hashlib,json,os,sys,time,traceback
from concurrent.futures import ThreadPoolExecutor
import psutil
import portable_paths as portable
import prepared_views
sys.path.insert(0,str(portable.SOURCES/'market'))
from worker_market import observe,atomic
from server16_py.memory_access import Memory
from inputs import Inputs
from engine import Market
from model import project
from screen import UI_SIGNATURE,build,waiting
from live_leagues import read as read_live_leagues
from save_sync import bind_pending
from asset_cache import revision as artwork_revision

GAME=portable.GAME;ROOT=GAME/'ModCarrerMode/runtime/manager_market';DEST=GAME/'data/ui/game/screens/career/server16/managermarket.big'
def package_key(model,ui_signature,art_revision=''):return hashlib.sha256((ui_signature+art_revision).encode()+json.dumps(model,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def view_scope(observed):
 s=observed['save'];p=observed['profile']
 return (s['pid'],s['process_created_100ns'],p['context_address'],p.get('context_epoch',0),p['club_id'],observed.get('date'),str(Path(s['path']).resolve()).casefold())

def render_package(request):
 path=request['package'];started=time.perf_counter();cached=path.is_file()
 if not cached:
  # Failed validation must never leave an apparently reusable cache entry.
  temporary=path.with_name(path.stem+'.building.big')
  try:build(GAME,temporary,request['model']);os.replace(temporary,path)
  finally:temporary.unlink(missing_ok=True)
 return cached,time.perf_counter()-started
def log(event,**values):
 ROOT.mkdir(parents=True,exist_ok=True)
 with (ROOT/'service.log').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**values),ensure_ascii=False)+'\n')
def io_event(saved):
 matches=[]
 for name in ('career_save_source.tsv','career_active_save.tsv'):
  try:
   d=dict(line.split('=',1) for line in (GAME/'ModCarrerMode/runtime'/name).read_text(encoding='utf-8-sig').splitlines() if '=' in line)
   if d.get('complete_file')=='1' and int(d['pid'])==saved['pid'] and int(d['process_created_100ns'])==saved['process_created_100ns'] and Path(d['path']).resolve()==Path(saved['path']).resolve():matches.append(d)
  except (ValueError,OSError,KeyError):pass
 return max(matches,key=lambda d:int(d.get('access_tick_ms',0)),default={})

class Service:
 def __init__(self,background=False):
  self.inputs=Inputs(GAME);self.market=None;self.last_io=None;self.last_signature=None;self.digest=None;self.context=None;self.owner=None;self.publication=None
  self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='manager-presentation') if background else None
  self.pending=None;self.latest_request=None;self.published_key=None;self.presentation_scope=None;self.model_revision=None;self.model_cache=None;self.render_retry=0;self.load_serial=0
 def close(self):
  if self.market:self.market.close()
  if self.executor:self.executor.shutdown(wait=False,cancel_futures=True)
 def presentation_wait(self,reason,**values):
  marker=(reason,repr(values))
  if marker!=getattr(self,'last_presentation_wait',None):log('presentation_wait',reason=reason,**values);self.last_presentation_wait=marker
 def publish(self,request,observed,memory,cached,build_seconds):
  if request['scope']!=self.presentation_scope or request['observed_scope']!=view_scope(observed):
   self.presentation_wait('changed_scope',request_scope=request['scope'],current_scope=self.presentation_scope,request_observation=request['observed_scope'],current_observation=view_scope(observed));return
  if memory is not None:
   latest=observe(memory)
   if latest['signature']!=observed['signature']:
    self.presentation_wait('changed_career',requested=observed['signature'],current=latest['signature']);return
  package=request['package'];blob=package.read_bytes();revision=hashlib.sha256(blob).hexdigest()
  if revision!=self.publication or not DEST.exists():atomic(DEST,blob)
  atomic(ROOT/'market.json',json.dumps(request['model'],ensure_ascii=False,separators=(',',':')).encode('utf8'))
  saved=observed['save'];context=request['context']
  atomic(ROOT/'active.json',json.dumps(dict(schema=1,pid=saved['pid'],created=saved['process_created_100ns'],save=saved['path'],database=str(self.market.path),branch=self.market.branch,date=context['date'],ready=True),ensure_ascii=False).encode('utf8'))
  self.publication=revision;self.published_key=request['key'];prepared_views.publish(ROOT/'view_ready.tsv',saved,observed['profile'],context['date'],revision)
  log('published',date=context['date'],clubs=len(request['model']['clubRows']),free=len(request['model']['freeRows']),dismissals=len(request['model']['moveRows']),seconds=round(time.perf_counter()-request['started'],3),input_engine_seconds=round(request['input_seconds'],3),model_seconds=round(request['model_seconds'],3),build_seconds=round(build_seconds,3),package_cached=cached,background_build=self.executor is not None)
 def service_render(self,observed,memory):
  if self.pending and self.pending[0].done():
   future,request=self.pending;self.pending=None
   try:
    cached,seconds=future.result();self.publish(request,observed,memory,cached,seconds)
   except Exception as exc:
    self.render_retry=time.monotonic()+5;log('presentation_failed',error=str(exc),traceback=traceback.format_exc())
  request=self.latest_request
  if self.pending or not request or request['key']==self.published_key or time.monotonic()<self.render_retry:return
  if request['scope']!=self.presentation_scope or request['observed_scope']!=view_scope(observed):
   self.presentation_wait('render_scope',request_scope=request['scope'],current_scope=self.presentation_scope,request_observation=request['observed_scope'],current_observation=view_scope(observed));return
  if request['package'].is_file():self.publish(request,observed,memory,True,0)
  elif self.executor:self.pending=(self.executor.submit(render_package,request),request);log('presentation_queued',date=request['context']['date'],key=request['key'])
  else:
   cached,seconds=render_package(request);self.publish(request,observed,memory,cached,seconds)
 def resume_handoff(self,observed,context,token):
  path=ROOT/'handoff.json'
  if not path.exists():return False
  try:
   handoff=json.loads(path.read_text(encoding='utf8'));path.unlink();saved=observed['save'];profile=observed['profile']
   if handoff.get('schema')!=1 or handoff.get('pid')!=saved['pid'] or handoff.get('created')!=saved['process_created_100ns'] or handoff.get('club')!=context['club'] or handoff.get('digest')!=context['digest'] or handoff.get('io')!=list(token) or handoff.get('context')!=profile['context_address'] or Path(handoff['save']).resolve()!=Path(saved['path']).resolve():return False
   branch=self.market.db.execute('SELECT * FROM branches WHERE id=?',(handoff['branch'],)).fetchone()
   if not branch or branch['game_date']!=handoff['date'] or branch['game_date']>context['date'] or branch['user_club']!=context['club']:return False
   self.market.branch=handoff['branch'];log('career_resumed_after_update',branch=self.market.branch,date=branch['game_date']);return True
  except (OSError,ValueError,KeyError,TypeError):return False
 def update(self,observed,memory):
  started=time.perf_counter()
  saved=observed['save'];io=io_event(saved)
  if io.get('operation') not in ('read','write'):raise ValueError('Aguardando identificação nativa do save')
  live_leagues=None
  if memory is not None:
   prepared_views.publish(ROOT/'read_request.tsv',saved,observed['profile'],observed['date'],'0'*64)
   try:live_leagues=read_live_leagues(ROOT/'live_leagues.tsv',observed,prepared_views.ticks())
   except (OSError,ValueError,KeyError,UnicodeError):pass
  token=(io.get('operation'),io.get('access_tick_ms'),saved['path']);snapshot=json.loads((GAME/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'))
  signature=(observed['signature'],observed['profile'].get('context_epoch',0),hashlib.sha256(json.dumps([snapshot.get('fixtures'),snapshot.get('standings')],separators=(',',':')).encode()).hexdigest(),token,live_leagues['revision'] if live_leagues else None)
  if signature==self.last_signature:
   self.service_render(observed,memory)
   if self.publication:prepared_views.publish(ROOT/'view_ready.tsv',saved,observed['profile'],observed.get('date',self.context['date']),self.publication)
   return
  context=self.inputs.read(observed,memory,live_leagues=live_leagues);path=Path(saved['path']);db_path=path.parent.parent/'server16_manager_market.sqlite3';digest=context['digest'];owner=(saved['pid'],saved['process_created_100ns'],observed['profile']['context_address'])
  fresh=self.market is None or self.market.path!=db_path
  if fresh:
   if self.market:self.market.close()
   self.market=Market(db_path,GAME/'ModCarrerMode/data/manager_market/catalog.sqlite3')
  with self.market.db:
   receipts=bind_pending(self.market,GAME)
   resumed=self.resume_handoff(observed,context,token) if fresh else False
   if not resumed and (fresh or owner!=self.owner or (token!=self.last_io and io.get('operation')=='read')):
    status=self.market.open_save(digest,path,context);log('career_'+status,database=str(db_path),branch=self.market.branch,date=context['date'])
   elif context['date']<self.market.info()['game_date']:
    self.market.open_save(digest,path,context);log('restored_after_date_rewind',date=context['date'])
   self.market.advance(context)
   native_bound=self.market.db.execute('SELECT 1 FROM save_receipts WHERE save_hash=? AND pid=? AND created=? AND write_ms=?',(digest,saved['pid'],saved['process_created_100ns'],int(io.get('access_tick_ms',0)))).fetchone()
   if io.get('operation')=='write' and token!=self.last_io and not native_bound and 'payload_crc32' not in io:self.market.checkpoint(digest,path,replace=True)
   state_revision=self.market.capture_session(saved['pid'],saved['process_created_100ns'],observed['profile']['context_address'],observed['profile'].get('context_epoch',0),prepared_views.ticks())
  # Simulation/persistence commits before rendering. A failed or stale UI build
  # must not replay this load and restore an earlier market on the next poll.
  self.context=context;self.digest=digest;self.last_io=token;self.owner=owner
  reload_save=token!=getattr(self,'presentation_io',None) and io.get('operation')=='read'
  if reload_save:self.load_serial+=1
  scope=(view_scope(observed),self.market.info()['career'],self.load_serial)
  if scope!=self.presentation_scope or reload_save:
   self.presentation_scope=scope;self.publication=None;self.published_key=None
   (ROOT/'view_ready.tsv').unlink(missing_ok=True)
   placeholder=ROOT/'waiting.big'
   if placeholder.exists():atomic(DEST,placeholder.read_bytes())
  self.presentation_io=token
  for receipt in receipts:log('save_checkpoint_bound',receipt_id=receipt['event'],**{k:v for k,v in receipt.items() if k!='event'})
  state=dict(schema=1,pid=saved['pid'],created=saved['process_created_100ns'],save=saved['path'],database=str(db_path),branch=self.market.branch,date=context['date'],digest=digest,context=observed['profile']['context_address'],epoch=observed['profile'].get('context_epoch',0),club=context['club'],io=list(token),revision=state_revision)
  atomic(ROOT/'state_ready.json',json.dumps(state,ensure_ascii=False,sort_keys=True).encode('utf8'))
  reviews=self.market.rows('reviews');movements=self.market.rows('movements');engine_status=dict(date=context['date'],branch=self.market.branch,tracking_start=self.market.info()['start_date'],coverage=context.get('coverage',{}),recorded_matches=len(self.market.rows('results')),evaluations=len(reviews),evaluations_today=sum(r['game_date']==context['date'] for r in reviews),dismissals=sum(r['kind']=='dismissal' for r in movements),hires=sum(r['kind'] in ('hired','interim_appointed') for r in movements),protected_club=context['club'],protected_club_market_events=sum(r['club_id']==context['club'] and r['kind'] in ('dismissal','resignation','hired','interim_appointed','poached','retirement') for r in movements))
  atomic(ROOT/'engine_status.json',json.dumps(engine_status,ensure_ascii=False,indent=2).encode('utf8'));log('engine_advanced',**engine_status)
  projected=time.perf_counter();model_revision=(state_revision,context.get('user_confidence'))
  if model_revision==self.model_revision and self.model_cache is not None:model,token_hash=self.model_cache
  else:
   model=project(self.market,user_confidence=context.get('user_confidence'));token_hash=package_key(model,UI_SIGNATURE,artwork_revision(GAME,model));self.model_cache=(model,token_hash);self.model_revision=model_revision
  prepared=time.perf_counter()
  package=ROOT/'packages'/('managers_'+token_hash+'.big')
  self.last_signature=signature
  self.latest_request=dict(model=model,key=token_hash,package=package,scope=scope,observed_scope=view_scope(observed),context=context,started=started,input_seconds=projected-started,model_seconds=prepared-projected)
  log('presentation_model_ready',date=context['date'],key=token_hash,cached=package.is_file(),seconds=round(prepared-projected,3))
  self.service_render(observed,memory)
  if self.publication:prepared_views.publish(ROOT/'view_ready.tsv',saved,observed['profile'],context['date'],self.publication)

def attach(process):
 """Memory has a zero-argument constructor, including the frozen Server16 API."""
 memory=Memory()
 try:
  memory.process_id=process.pid
  memory.process_handle=memory.kernel32.OpenProcess(0x410,False,process.pid)
  if not memory.process_handle:raise OSError('FIFA não permite leitura')
  memory.base_module=memory._get_base_address(process.exe())
  if not memory.base_module:raise OSError('Aguardando o módulo do FIFA carregar')
  if memory.read_process_memory(memory.base_module,2)!=b'MZ':raise OSError('Módulo do FIFA não reconhecido')
  return memory
 except Exception:
  memory.close();raise

def main():
 try:
  process=portable.session_process();created=process.create_time();memory=attach(process)
 except (OSError,RuntimeError,psutil.NoSuchProcess,psutil.AccessDenied) as exc:
  log('waiting',error=str(exc));return
 import ctypes
 from ctypes import wintypes
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 lock=kernel.CreateMutexW(None,False,'Local\\Server16ManagerMarket_'+str(process.pid))
 if not lock or ctypes.get_last_error()==183:
  if lock:kernel.CloseHandle(lock)
  memory.close();return
 service=None;error=None
 try:
  service=Service(background=True)
  (ROOT/'view_ready.tsv').unlink(missing_ok=True)
  placeholder=ROOT/'waiting.big';build(GAME,placeholder,waiting());atomic(DEST,placeholder.read_bytes());log('started',pid=process.pid)
  while process.is_running() and process.create_time()==created and not (ROOT/'STOP').exists():
   try:service.update(observe(memory),memory);error=None
   except Exception as exc:
    message=str(exc)
    if message!=error:log('waiting',error=message);error=message
   time.sleep(2)
 except psutil.NoSuchProcess:pass
 except Exception as exc:log('failed',error=str(exc),traceback=traceback.format_exc())
 finally:
  if service:service.close()
  memory.close();kernel.CloseHandle(lock);log('stopped',pid=os.getpid())

if __name__=='__main__':main()
