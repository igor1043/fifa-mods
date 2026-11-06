"""Keep real dated league observations while presentation/SQL work is busy."""
from collections import OrderedDict
from threading import Event,Lock,Thread
from pathlib import Path
import hashlib,json,zlib

def scope(observed,token):
 s=observed['save'];p=observed['profile']
 return s['pid'],s['process_created_100ns'],p['context_address'],p.get('context_epoch',0),p['club_id'],str(s['path']).casefold(),tuple(token)

def same_session(previous,current):
 # A completed write belongs to the current loaded career. Preserve the
 # intervening dated observations until the engine has caught up to that
 # save. A new read (even the same file/date) always starts a fresh timeline.
 return previous==current or bool(previous and previous[:-1]==current[:-1] and current[-1][0]=='write')

class Sampler:
 def __init__(self,process,game,root,observe,attach,io_event,read,publish,ticks):
  self.process=process;self.game=game;self.root=root;self.observe=observe;self.attach=attach;self.io=io_event;self.read=read;self.publish=publish;self.ticks=ticks
  self.journal_stamps={};self.retained_revisions={};self.journal_floor=0;self.stop=Event();self.lock=Lock();self.samples=OrderedDict();self.owner=None;self.thread=Thread(target=self.run,daemon=True,name='manager-live-sampler')
 def start(self):self.thread.start()
 def close(self):self.stop.set();self.thread.join(timeout=2)
 def retain(self,observed,token,live):
  owner=scope(observed,token)
  with self.lock:
   if not same_session(self.owner,owner):self.samples.clear();self.retained_revisions.clear()
   self.owner=owner
   row_revision=live.get('revision') or hashlib.sha256(json.dumps(live['rows'],sort_keys=True).encode()).hexdigest()
   campaign_revision=hashlib.sha256(json.dumps(live['snapshot'],sort_keys=True).encode()).hexdigest() if live.get('snapshot') else None
   seen=self.retained_revisions.get(live['date'])
   if seen and seen[0]==row_revision and (campaign_revision is None or campaign_revision==seen[1]):return
   self.retained_revisions[live['date']]=(row_revision,campaign_revision or (seen[1] if seen else None))
   old=self.samples.get(live['date'])
   previous=json.loads(zlib.decompress(old['payload'])) if old else {}
   payload=dict(rows=live['rows'],snapshot=live.get('snapshot') or previous.get('snapshot'))
   encoded=zlib.compress(json.dumps(payload,separators=(',',':')).encode(),1)
   if old and old['payload']==encoded:return
   self.samples[live['date']]=dict(date=live['date'],revision=live.get('revision'),payload=encoded)
   while len(self.samples)>512:self.samples.popitem(last=False)
 def drain(self,observed,token,after):
  self.journal_floor=after
  self.capture_journal(observed,token)
  with self.lock:
   if not same_session(self.owner,scope(observed,token)):return []
   dates=sorted(d for d in self.samples if d<=observed['date']);result=[dict(date=d,**json.loads(zlib.decompress(self.samples[d]['payload']))) for d in dates if d>=after]
   for d in dates:self.samples.pop(d,None)
   return result
 def capture_journal(self,observed,token):
  if self.root is None:return
  from live_leagues import read,read_campaign
  s=observed['save'];p=observed['profile']
  folder=Path(self.root)/'league_days'/f"{s['pid']}-{s['process_created_100ns']}-{p['context_epoch']}-{p['context_address']:x}"
  try:dates={int(p.name.split('.')[0]) for pattern in ('*.tsv','*.campaign.json') for p in folder.glob(pattern) if p.name.split('.')[0].isdigit()}
  except OSError:return
  for date in sorted(dates):
   try:
    if not self.journal_floor<=date<=observed['date']:continue
    path=folder/(str(date)+'.tsv');campaign=folder/(str(date)+'.campaign.json')
    def stamp(p):
     try:s=p.stat();return s.st_mtime_ns,s.st_size
     except OSError:return None
    key=(stamp(path),stamp(campaign))
    with self.lock:
     if self.journal_stamps.get(str(path))==key:continue
    # Archived samples belong to the exact native context/load and retain
    # their original day; their age is expected when the worker catches up.
    live=dict(date=date,rows=[])
    if key[0] is not None:live=read(path,dict(observed,date=date),self.ticks(),max_age_ms=None)
    if key[1] is not None:live['snapshot']=read_campaign(campaign,dict(observed,date=date))
    self.retain(observed,token,live)
    with self.lock:self.journal_stamps[str(path)]=key
   except (OSError,ValueError,KeyError,RuntimeError):continue
 def run(self):
  memory=None
  try:
   memory=self.attach(self.process)
   while not self.stop.is_set() and self.process.is_running():
    try:
     observed=self.observe(memory);s=observed['save'];io=self.io(s);token=(io.get('operation'),io.get('access_tick_ms'),s['path'])
     if io.get('operation') in ('read','write'):
      self.publish(self.root/'read_request.tsv',s,observed['profile'],observed['date'],'0'*64)
      self.capture_journal(observed,token)
      live=self.read(self.root/'live_leagues.tsv',observed,self.ticks());self.retain(observed,token,live)
    except (OSError,ValueError,KeyError,RuntimeError):pass
    self.stop.wait(.2)
  except (OSError,RuntimeError):pass
  finally:
   if memory:memory.close()

def replay(market,context,samples):
 with market.db.read_batch():return _replay(market,context,samples)

def _replay(market,context,samples):
 from calendar import monthrange
 from datetime import date
 policy=market.policy()
 due={a['contract_end'] for a in market.rows('appointments','end_date IS NULL')}
 due.update(r['date'] for name in ('titles','cup_exits') for r in context.get(name,[]))
 due.update(m['date'] for m in context['fixtures'] if m['played'])
 for coach in market.rows('coaches'):
  try:
   born=date.fromisoformat(coach['birth_date']);retirement=born.replace(year=born.year+int(policy['retirement_age']));due.add(retirement.year*10000+retirement.month*100+retirement.day)
  except (ValueError,TypeError):pass
 samples=[s for s in samples if s.get('snapshot') and market.info()['game_date']<=s['date']<=context['date']]
 processed=[];previous=None
 for index,sample in enumerate(samples):
  today=sample['date']
  if not market.info()['game_date']<=today<=context['date']:continue
  # leagueteamlinks can retain January totals throughout fast simulation.
  # Its timestamp alone must never move the football simulation's cursor.
  if not sample.get('snapshot'):continue
  snapshot=sample['snapshot']
  # Unchanged football evidence cannot reroll a board decision. Preserve
  # calendar deadlines, month/year boundaries and the final observed date.
  key=tuple(snapshot.get(k) for k in ('nodes','standings','standingGoals','fixtures'))+(sample['rows'],)
  month=today//100%100;day=today%100;month_end=day==monthrange(today//10000,month)[1]
  changed=key!=previous
  deadline=today in due or bool(market.db.execute('SELECT 1 FROM appointments WHERE branch=? AND end_date IS NULL AND contract_end<=? LIMIT 1',(market.branch,today)).fetchone())
  if index and index<len(samples)-1 and not changed and not deadline and not month_end and today%10000!=101:continue
  c=calendar_context(context,sample['snapshot'],sample['rows'])
  market.advance(c);processed.append(today);previous=key
  if getattr(market,'market_progress',None):market.market_progress.market_day(today,complete=True)
 return processed

def calendar_context(context,snapshot,rows):
 from global_performance import project
 today=snapshot['date'];members={c['club_id']:c['league_id'] for c in context['clubs']}
 fixtures=dated_fixtures(snapshot,context['fixtures'],context['season'])
 evidence=project(snapshot,fixtures,members,rows,today,context['season'],today,'live_league')
 for row in evidence['performance']:
  if row['source']=='fce':row['source']='native_view'
 return dict(context,date=today,fixtures=fixtures,coverage=dict(evidence.get('coverage',{}),calendar_native=True),performance=evidence['performance'],tables=evidence['tables'],club_tables=evidence['club_tables'],table_dates=evidence['table_dates'])


def dated_fixtures(snapshot,known,season):
 nodes={r[0]:r for r in snapshot.get('nodes',[])};fixtures={m['id']:m for m in known}
 for f in snapshot.get('fixtures',[]):
  node=f[1];seen=set();root=None
  while node in nodes and node not in seen:
   seen.add(node);r=nodes[node]
   if r[2]==3:root=r;break
   node=r[1]
  if root is None or f[5]<=0 or f[6]<=0 or f[5]==f[6]:continue
  old=fixtures.get(f[0],{});played=f[9]==1 and 0<=f[7]<100 and 0<=f[8]<100
  fixtures[f[0]]=dict(id=f[0],root=root[0],asset=root[3],stage=f[2],kind=old.get('kind',0),date=f[3],home=f[5],away=f[6],hg=f[7] if played else None,ag=f[8] if played else None,played=played,season=season)
 return list(fixtures.values())
