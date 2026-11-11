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
  self.drained_files={};self.committed_files={};self.journal_stamps={};self.retained_revisions={};self.journal_floor=0;self.stop=Event();self.lock=Lock();self.samples=OrderedDict();self.owner=None;self.thread=Thread(target=self.run,daemon=True,name='manager-live-sampler')
 def start(self):self.thread.start()
 def close(self):self.stop.set();self.thread.join(timeout=2)
 def retain(self,observed,token,live,journal=()):
  owner=scope(observed,token)
  with self.lock:
   if not same_session(self.owner,owner):self.samples.clear();self.retained_revisions.clear()
   self.owner=owner
   row_revision=live.get('revision') or hashlib.sha256(json.dumps(live['rows'],sort_keys=True).encode()).hexdigest()
   if live.get('national_job'):row_revision+=':nation:'+str(live['national_job']['team'])
   campaign_revision=hashlib.sha256(json.dumps(live['snapshot'],sort_keys=True).encode()).hexdigest() if live.get('snapshot') else None
   seen=self.retained_revisions.get(live['date'])
   old=self.samples.get(live['date'])
   if seen and seen[0]==row_revision and (campaign_revision is None or campaign_revision==seen[1]):
    if old and journal:old['journal']=journal
    return
   self.retained_revisions[live['date']]=(row_revision,campaign_revision or (seen[1] if seen else None))
   previous=json.loads(zlib.decompress(old['payload'])) if old else {}
   snapshot=live.get('snapshot') or previous.get('snapshot')
   job=live.get('national_job') or previous.get('national_job')
   if snapshot and job:snapshot=dict(snapshot,national_job=job)
   payload=dict(rows=live['rows'],snapshot=snapshot,national_job=job)
   encoded=zlib.compress(json.dumps(payload,separators=(',',':')).encode(),1)
   files=journal or (old.get('journal',()) if old else ())
   self.samples[live['date']]=dict(date=live['date'],revision=live.get('revision'),payload=encoded,journal=files)
   while len(self.samples)>512:self.samples.popitem(last=False)
 def drain(self,observed,token,after):
  self.journal_floor=after
  self.capture_journal(observed,token)
  with self.lock:
   self.drained_files={}
   if not same_session(self.owner,scope(observed,token)):return []
   dates=sorted(d for d in self.samples if d<=observed['date']);result=[]
   for day in dates:
    item=self.samples.pop(day)
    if day<after:continue
    decoded=json.loads(zlib.decompress(item['payload']))
    result.append(dict(date=day,**decoded))
    if decoded.get('snapshot'):
     self.drained_files.update({(day,path):stamp for path,stamp in item['journal']})
   return result
 def discard_committed(self,through):
  if self.root is None:return
  from server16_py.session_storage import prune_committed_calendar
  self.committed_files.update(self.drained_files);self.drained_files={}
  prune_committed_calendar(self.root,self.committed_files,through)
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
    files=tuple((p,s) for p,s in zip((path,campaign),key) if s is not None)
    self.retain(observed,token,live,files)
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
      live=self.read(self.root/'live_leagues.tsv',observed,self.ticks())
      try:
       from national_title_context import live_team
       live['national_job']=dict(date=observed['date'],team=live_team(memory,observed['profile']),source='live_context')
      except (OSError,RuntimeError,ValueError,KeyError):pass
      self.retain(observed,token,live)
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
 from title_evidence import completed_titles,merge_scores
 formats=context.get('title_formats',{});labels=context.get('title_labels',{})
 leagues={lid:dict(members={c['club_id'] for c in context['clubs'] if c['league_id']==lid}) for lid in set(members.values())}
 title_start=context.get('title_start',context['season'])
 title_fixtures=merge_scores(context.get('title_fixtures',[dict(m,stageKind=m['kind'],homeScore=m['hg'],awayScore=m['ag']) for m in fixtures]),snapshot,title_start)
 title_rows=completed_titles(title_fixtures,formats,leagues,today,title_start,lambda i:labels.get(i,'Competição '+str(i)))
 titles=[dict(t,asset=t['competition']) for t in title_rows] if formats else context.get('titles',[])
 jobs=[j for j in context.get('national_jobs',[]) if j['date']<=today]
 if snapshot.get('national_job'):jobs.append(snapshot['national_job'])
 return dict(context,date=today,national_jobs=jobs,fixtures=fixtures,titles=titles,title_fixtures=title_fixtures,coverage=dict(evidence.get('coverage',{}),calendar_native=True),performance=evidence['performance'],tables=evidence['tables'],club_tables=evidence['club_tables'],table_dates=evidence['table_dates'])


def dated_fixtures(snapshot,known,season):
 from title_evidence import merge_scores,season_of
 source=[dict(m,stageKind=m['kind'],homeScore=m['hg'],awayScore=m['ag']) for m in known]
 merged=merge_scores(source,snapshot,season)
 return [dict(id=m['id'],root=m['root'],asset=m['asset'],stage=m['stage'],kind=m['stageKind'],date=m['date'],home=m['home'],away=m['away'],hg=m['homeScore'],ag=m['awayScore'],played=m['played'],season=season_of(m['date'],season)) for m in merged]
