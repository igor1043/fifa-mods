"""Keep real dated league observations while presentation/SQL work is busy."""
from collections import OrderedDict
from threading import Event,Lock,Thread
import json,zlib

def scope(observed,token):
 s=observed['save'];p=observed['profile']
 return s['pid'],s['process_created_100ns'],p['context_address'],p.get('context_epoch',0),p['club_id'],str(s['path']).casefold(),tuple(token)

class Sampler:
 def __init__(self,process,game,root,observe,attach,io_event,read,publish,ticks):
  self.process=process;self.game=game;self.root=root;self.observe=observe;self.attach=attach;self.io=io_event;self.read=read;self.publish=publish;self.ticks=ticks
  self.stop=Event();self.lock=Lock();self.samples=OrderedDict();self.owner=None;self.thread=Thread(target=self.run,daemon=True,name='manager-live-sampler')
 def start(self):self.thread.start()
 def close(self):self.stop.set();self.thread.join(timeout=2)
 def retain(self,observed,token,live):
  owner=scope(observed,token)
  with self.lock:
   if owner!=self.owner:self.samples.clear();self.owner=owner
   signature=live.get('revision')
   old=self.samples.get(live['date'])
   if old and signature is not None and old['revision']==signature:return
   self.samples[live['date']]=dict(date=live['date'],revision=signature,payload=zlib.compress(json.dumps(live['rows'],separators=(',',':')).encode(),1))
   while len(self.samples)>512:self.samples.popitem(last=False)
 def drain(self,observed,token,after):
  with self.lock:
   if self.owner!=scope(observed,token):return []
   dates=sorted(d for d in self.samples if d<=observed['date']);result=[dict(date=d,rows=json.loads(zlib.decompress(self.samples[d]['payload']))) for d in dates if d>after]
   for d in dates:self.samples.pop(d,None)
   return result
 def run(self):
  memory=None
  try:
   memory=self.attach(self.process)
   while not self.stop.is_set() and self.process.is_running():
    try:
     observed=self.observe(memory);s=observed['save'];io=self.io(s);token=(io.get('operation'),io.get('access_tick_ms'),s['path'])
     if io.get('operation') in ('read','write'):
      self.publish(self.root/'read_request.tsv',s,observed['profile'],observed['date'],'0'*64)
      live=self.read(self.root/'live_leagues.tsv',observed,self.ticks());self.retain(observed,token,live)
    except (OSError,ValueError,KeyError,RuntimeError):pass
    self.stop.wait(.5)
  except (OSError,RuntimeError):pass
  finally:
   if memory:memory.close()

def replay(market,context,samples):
 from global_performance import project
 members={c['club_id']:c['league_id'] for c in context['clubs']}
 for sample in samples:
  today=sample['date']
  if not market.info()['game_date']<today<=context['date']:continue
  evidence=project(dict(date=today,nodes=[],standings=[]),context['fixtures'],members,sample['rows'],today,context['season'],today,'live_league')
  c=dict(context,date=today,performance=evidence['performance'],tables=evidence['tables'],club_tables=evidence['club_tables'],table_dates=evidence['table_dates'])
  market.advance(c)
