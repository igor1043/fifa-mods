"""Independent read-only CV responder; calendar simulation never queues clicks.

Own SQLite connection and process reader. A context/catalog/date/data-version
change invalidates results before publication. No simulation or finance writes.
"""
from pathlib import Path
from collections import OrderedDict
from threading import Event,Thread
import sqlite3,time
from engine import Market
from read_batch import Connection


class ReadOnlyMarket:
 def __init__(self,path,catalog,branch):
  name=str(path)
  if name.startswith('\\\\?\\UNC\\'):name='\\\\'+name[8:]
  elif name.startswith('\\\\?\\'):name=name[4:]
  self.path=Path(name);self.catalog=Path(catalog);self.branch=branch
  self.db=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.1,factory=Connection)
  self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA query_only=ON')
 def close(self):self.db.close()
 def rows(self,table,where='',args=()):
  # Parentheses keep OR clauses inside the branch, including club history.
  return Market.rows(self,table,'('+where+')' if where else '',args)
 def one(self,table,key,value):return Market.one(self,table,key,value)
 def info(self):return Market.info(self)
 def version(self):return self.db.execute('PRAGMA data_version').fetchone()[0]


class DetailResponder:
 def __init__(self,root,game,process,context,observe,attach,ticks,publish,log):
  self.root=Path(root);self.game=Path(game);self.process=process;self.context=context
  self.observe=observe;self.attach=attach;self.ticks=ticks;self.publish=publish;self.log=log
  self.stop=Event();self.thread=Thread(target=self.run,daemon=True,name='manager-cv-responder')
  self.reader=None;self.reader_key=None;self.cache=OrderedDict();self.completed={};self.stamps={};self.prepared=set()
 def start(self):self.thread.start()
 def close(self):
  self.stop.set();self.thread.join(timeout=3)
 def current(self,context,observed):
  s=observed['save'];p=observed['profile']
  scope=(s['pid'],s['process_created_100ns'],p['context_address'],p.get('context_epoch',0),p['club_id'],observed.get('date'),str(Path(s['path']).resolve()).casefold())
  return context['scope']==scope
 def connect(self,context):
  key=(str(context['path']),context['branch'])
  if self.reader_key!=key:
   if self.reader:self.reader.close()
   self.reader=ReadOnlyMarket(context['path'],context['catalog'],context['branch'])
   self.reader_key=key;self.cache.clear();self.completed.clear();self.prepared.clear()
  return self.reader
 def tick(self,memory):
  context=self.context()
  if not context:return
  for kind,filename in (('profile','profile_request.tsv'),('history','history_request.tsv')):
   path=self.root/filename
   try:stat=path.stat()
   except OSError:continue
   signature=(context['generation'],stat.st_mtime_ns,stat.st_size)
   if self.stamps.get(kind)==signature:continue
   observed=self.observe(memory)
   if not self.current(context,observed):continue
   if kind=='profile':
    from profile_request import read
    request=read(path,observed,context['base'],self.ticks());identity=request['identity'];ident=request['coach']
   else:
    from club_history import request as read
    request=read(path,observed,context['base'],self.ticks());identity=request['identity'];ident=request['club']
   if not ident and kind=='profile' and request.get('person')==-1:
    displayed=request.get('resume',{}).get('focus',-1)
    if 0<=displayed<len(context['base']['people']):self.log('profile_displayed',coach=context['base']['people'][displayed]['id'],date=context['base']['date'],native_tick=identity[0])
   if not ident or self.completed.get(kind)==(context['generation'],identity):
    self.stamps[kind]=signature;continue
   started=time.perf_counter();reader=self.connect(context);version=reader.version()
   cache_key=(context['generation'],version,kind,ident);cached=cache_key in self.cache
   if not cached:
    reader.db.execute('BEGIN')
    try:
     if reader.info()['game_date']!=context['base']['date']:continue
     with reader.db.read_batch():
      if kind=='profile':
       from profile_query import build
       data=build(reader,context['base']['people'][request['person']],context.get('user_confidence'))
       if data['id']!=ident:raise ValueError('Perfil substituído durante a consulta')
      else:
       from club_history import build
       data=build(reader,ident,context['base']['people'])
    finally:reader.db.rollback()
    if reader.version()!=version:continue
    self.cache[cache_key]=data
    while len(self.cache)>16:
     expired,_=self.cache.popitem(last=False);self.prepared.discard(expired)
   data=self.cache[cache_key];self.cache.move_to_end(cache_key)
   current=self.context()
   if (not current or current['generation']!=context['generation'] or not self.current(context,self.observe(memory))
       or reader.version()!=version):continue
   if cache_key in self.prepared:
    self.completed[kind]=(context['generation'],identity);self.stamps[kind]=signature
    self.log('detail_cache_hit',kind=kind,ident=ident,click_age_ms=max(0,self.ticks()-identity[0]));continue
   if kind=='profile':
    from screen import profile_payload
    from profile_media import describe
    payload=dict(kind='profile',token=context['base'].get('profileToken',''),person=request['person'],date=context['base']['date'],encoded=profile_payload(data),artwork=describe(data,context['base'].get('artworkRevision','')))
   else:payload=dict(kind='history',token=context['base'].get('profileToken',''),club=ident,date=context['base']['date'],data=data)
   self.publish(self.game,self.root,'manager'+kind,payload);self.prepared.add(cache_key)
   self.completed[kind]=(context['generation'],identity);self.stamps[kind]=signature
   self.log('detail_response',kind=kind,ident=ident,cached=cached,seconds=round(time.perf_counter()-started,4),
            click_age_ms=max(0,self.ticks()-identity[0]),independent_reader=True)
 def run(self):
  memory=None;last_error=None
  try:
   memory=self.attach(self.process)
   while not self.stop.is_set() and self.process.is_running():
    try:self.tick(memory);last_error=None
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,sqlite3.Error) as exc:
     message=str(exc)
     if message!=last_error:self.log('detail_waiting',error=message);last_error=message
    self.stop.wait(.05)
  finally:
   if self.reader:self.reader.close()
   if memory:memory.close()
