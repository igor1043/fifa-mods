"""Career-scoped coach market. SQLite facts, deterministic reviews, no FIFA writes."""
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
import hashlib,json,sqlite3,uuid,zlib

DEFAULTS=dict(max_dismissals_year=3,min_tenure_days=60,min_tenure_games=8,review_gap_days=7,
 pressure_threshold=32,max_dismissal_bps=2500,resignation_bps=4,poach_bps=800,dismissal_slope_bps=90,
 position_weight=50,form_weight=25,points_weight=20,relegation_weight=15,cup_weight=18,
 contract_months=24,compensation_months=3,renewal_months=12,enabled=1,
 retirement_age=80,minimum_free_coaches=60,regens_enabled=1,market_policy_version=2)
SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS branches(id TEXT PRIMARY KEY,career TEXT NOT NULL,start_date INT NOT NULL,game_date INT NOT NULL,season INT NOT NULL,user_club INT NOT NULL,seed TEXT NOT NULL,kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS save_checkpoints(save_hash TEXT PRIMARY KEY,save_path TEXT NOT NULL,branch TEXT NOT NULL,game_date INT NOT NULL,state BLOB);
CREATE TABLE IF NOT EXISTS coaches(branch TEXT,coach_id TEXT,name TEXT,nationality TEXT,birth_date TEXT,reputation REAL,salary INT,style TEXT,image TEXT,eligible INT,fictional INT,PRIMARY KEY(branch,coach_id));
CREATE TABLE IF NOT EXISTS clubs(branch TEXT,club_id INT,name TEXT,league_id INT,league_name TEXT,country TEXT,region TEXT,reputation REAL,budget INT,level INT,PRIMARY KEY(branch,club_id));
CREATE TABLE IF NOT EXISTS appointments(branch TEXT,id TEXT,coach_id TEXT,club_id INT,start_date INT,end_date INT,end_reason TEXT,monthly_wage INT,contract_end INT,origin TEXT,PRIMARY KEY(branch,id));
CREATE UNIQUE INDEX IF NOT EXISTS one_active_club ON appointments(branch,club_id) WHERE end_date IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS one_active_coach ON appointments(branch,coach_id) WHERE end_date IS NULL;
CREATE TABLE IF NOT EXISTS movements(branch TEXT,id TEXT,game_date INT,coach_id TEXT,club_id INT,from_club INT,to_club INT,kind TEXT,reason TEXT,old_salary INT,new_salary INT,pressure REAL,PRIMARY KEY(branch,id));
CREATE TABLE IF NOT EXISTS results(branch TEXT,match_key TEXT,season INT,root INT,competition_id INT,stage INT,game_date INT,home INT,away INT,hg INT,ag INT,home_coach TEXT,away_coach TEXT,home_appointment TEXT,away_appointment TEXT,PRIMARY KEY(branch,match_key));
CREATE INDEX IF NOT EXISTS result_home_coach ON results(branch,home_coach);
CREATE INDEX IF NOT EXISTS result_away_coach ON results(branch,away_coach);
CREATE TABLE IF NOT EXISTS honours(branch TEXT,coach_id TEXT,club_id INT,season INT,competition_id INT,root INT,game_date INT,name TEXT,PRIMARY KEY(branch,season,root,club_id));
CREATE TABLE IF NOT EXISTS reviews(branch TEXT,club_id INT,game_date INT,pressure REAL,position INT,expected_position INT,reason TEXT,decision TEXT,PRIMARY KEY(branch,club_id,game_date));
CREATE TABLE IF NOT EXISTS cup_exits(branch TEXT,root INT,club_id INT,game_date INT,prestige INT,PRIMARY KEY(branch,root,club_id,game_date));
CREATE TABLE IF NOT EXISTS competition_policies(branch TEXT,competition_id INT,name TEXT,prestige INT,PRIMARY KEY(branch,competition_id));
CREATE TABLE IF NOT EXISTS market_rules(branch TEXT,key TEXT,value REAL,PRIMARY KEY(branch,key));
CREATE TABLE IF NOT EXISTS salary_events(branch TEXT,id TEXT,coach_id TEXT,club_id INT,game_date INT,amount INT,kind TEXT,PRIMARY KEY(branch,id));
CREATE TABLE IF NOT EXISTS progress(branch TEXT,club_id INT,last_review INT,PRIMARY KEY(branch,club_id));
CREATE TABLE IF NOT EXISTS performance_evidence(branch TEXT,season INT,competition_key TEXT,club_id INT,game_date INT,hw INT,hd INT,hl INT,aw INT,ad INT,al INT,source TEXT,PRIMARY KEY(branch,season,competition_key,club_id));
CREATE TABLE IF NOT EXISTS appointment_baselines(branch TEXT,appointment TEXT,season INT,competition_key TEXT,played INT,PRIMARY KEY(branch,appointment,season,competition_key));
CREATE TABLE IF NOT EXISTS session_states(pid INT,created INT,context INT,epoch INT,captured_ms INT,branch TEXT,game_date INT,state_hash TEXT,state BLOB,PRIMARY KEY(pid,created,context,captured_ms));
CREATE TABLE IF NOT EXISTS save_receipts(event_id TEXT PRIMARY KEY,save_hash TEXT,branch TEXT,game_date INT,pid INT,created INT,write_ms INT,source TEXT);
PRAGMA user_version=4;
'''
TABLES=('coaches','clubs','appointments','movements','results','honours','reviews','cup_exits','competition_policies','market_rules','salary_events','progress','performance_evidence','appointment_baselines')

def day(value):return date(value//10000,value//100%100,value%100)
def packed(d):return d.year*10000+d.month*100+d.day
def elapsed(a,b):return (day(b)-day(a)).days
def after_months(value,n):
 d=day(value);m=d.year*12+d.month-1+n;y,m=divmod(m,12)
 from calendar import monthrange
 return y*10000+(m+1)*100+min(d.day,monthrange(y,m+1)[1])
def draw(seed,*parts):return int.from_bytes(hashlib.sha256(('|'.join(map(str,(seed,*parts)))).encode()).digest()[:8],'big')%10000
def score(rows):
 out=dict(games=0,wins=0,draws=0,losses=0,gf=0,ga=0)
 for gf,ga in rows:
  out['games']+=1;out['wins']+=gf>ga;out['draws']+=gf==ga;out['losses']+=gf<ga;out['gf']+=gf;out['ga']+=ga
 out['points']=out['wins']*3+out['draws'];out['percentage']=round(100*out['points']/(3*out['games']),1) if out['games'] else 0
 return out

class Market:
 def __init__(self,path,catalog):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(self.path,timeout=15);self.db.row_factory=sqlite3.Row
  version=self.db.execute('PRAGMA user_version').fetchone()[0]
  if version not in (0,1,2,3,4):raise ValueError('Versão do mercado de técnicos não suportada')
  self.db.executescript(SCHEMA)
  if 'state' not in {r[1] for r in self.db.execute('PRAGMA table_info(save_checkpoints)')}:self.db.execute('ALTER TABLE save_checkpoints ADD COLUMN state BLOB')
  columns={r[1] for r in self.db.execute('PRAGMA table_info(results)')}
  for name in ('home_appointment','away_appointment'):
   if name not in columns:self.db.execute('ALTER TABLE results ADD COLUMN '+name+' TEXT')
  self.catalog=Path(catalog);self.branch=None
 def close(self):self.db.close()
 def rows(self,table,where='',args=()):
  if table not in TABLES:raise ValueError('Tabela inválida')
  return [dict(x) for x in self.db.execute('SELECT * FROM '+table+' WHERE branch=?'+(' AND '+where if where else ''),(self.branch,*args))]
 def add(self,table,values):
  if table not in TABLES:raise ValueError('Tabela inválida')
  values=dict(branch=self.branch,**values);cols=','.join(values)
  self.db.execute('INSERT INTO '+table+' ('+cols+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))
 def info(self):return dict(self.db.execute('SELECT * FROM branches WHERE id=?',(self.branch,)).fetchone())
 def clone(self,source,kind='live'):
  new=uuid.uuid4().hex;row=dict(self.db.execute('SELECT * FROM branches WHERE id=?',(source,)).fetchone());row.update(id=new,kind=kind)
  self.db.execute('INSERT INTO branches VALUES(?,?,?,?,?,?,?,?)',tuple(row.values()))
  for table in TABLES:
   columns=[r[1] for r in self.db.execute('PRAGMA table_info('+table+')') if r[1]!='branch'];names=','.join(columns)
   self.db.execute('INSERT INTO '+table+' (branch,'+names+') SELECT ?,'+names+' FROM '+table+' WHERE branch=?',(new,source))
  return new
 def open_save(self,digest,path,context):
  with self.db:
   found=self.db.execute('SELECT branch,state FROM save_checkpoints WHERE save_hash=?',(digest,)).fetchone()
   if found:
    if found['state']:
     state=json.loads(zlib.decompress(found['state']));row=state['info'];new=uuid.uuid4().hex;row.update(id=new,kind='live');self.db.execute('INSERT INTO branches VALUES(?,?,?,?,?,?,?,?)',tuple(row.values()));self.branch=new
     for table,content in state['tables'].items():
      if table not in TABLES:raise ValueError('Tabela desconhecida no checkpoint')
      cols=content['columns'];query='INSERT INTO '+table+' (branch,'+','.join(cols)+') VALUES('+','.join('?' for _ in range(len(cols)+1))+')';self.db.executemany(query,[(new,*r) for r in content['rows']])
    else:self.branch=self.clone(found['branch'])
    return 'restored'
   self.branch=uuid.uuid4().hex;today=context.get('saved_date',context['date']);career=uuid.uuid4().hex;seed_context=dict(context,date=today,club=context.get('saved_club',context['club']))
   self.db.execute('INSERT INTO branches VALUES(?,?,?,?,?,?,?,?)',(self.branch,career,today,today,context['season'],context['club'],career,'live'))
   cat=sqlite3.connect(self.catalog);cat.row_factory=sqlite3.Row
   for table in ('coaches','clubs'):
    for r in cat.execute('SELECT * FROM '+table):self.add(table,dict(r))
   catalog_policy={r[0]:r[1] for r in cat.execute('SELECT key,value FROM rules')};policy=dict(DEFAULTS);policy.update(catalog_policy)
   policy['market_policy_version']=catalog_policy.get('market_policy_version',1)
   for k,v in policy.items():self.add('market_rules',dict(key=k,value=v))
   self.sync_clubs(context)
   for r in cat.execute('SELECT * FROM club_seed ORDER BY priority DESC,club_id'):
    club=self.one('clubs','club_id',r['club_id']);coach=self.one('coaches','coach_id',r['coach_id'])
    if club and coach and not self.active(coach=coach['coach_id']):self.appoint(coach,club,today,'initial',initial=True,started=context.get('career_start_date'))
   cat.close();self.ensure_user(seed_context,today)
   # Existing results predate the observed appointment, so do not assign them
   # to today's coach. They may still inform league position, never lifetime stats.
   self.ingest(context['fixtures'],today,baseline=True)
   self.checkpoint(digest,path)
  return 'created'
 def snapshot(self):
  tables={}
  for table in TABLES:
   cols=[r[1] for r in self.db.execute('PRAGMA table_info('+table+')') if r[1]!='branch'];tables[table]=dict(columns=cols,rows=[list(r) for r in self.db.execute('SELECT '+','.join(cols)+' FROM '+table+' WHERE branch=?',(self.branch,))])
  return zlib.compress(json.dumps(dict(info=self.info(),tables=tables),ensure_ascii=False,separators=(',',':')).encode(),6)
 def checkpoint(self,digest,path,replace=False,state=None):
  if not replace and self.db.execute('SELECT 1 FROM save_checkpoints WHERE save_hash=?',(digest,)).fetchone():return False
  state=self.snapshot() if state is None else state;info=json.loads(zlib.decompress(state))['info']
  self.db.execute('INSERT OR REPLACE INTO save_checkpoints VALUES(?,?,?,?,?)',(digest,str(path),info['id'],info['game_date'],state));return True
 def capture_session(self,pid,created,context,epoch,captured_ms):
  state=self.snapshot();digest=hashlib.sha256(state).hexdigest()
  last=self.db.execute('SELECT state_hash,epoch FROM session_states WHERE pid=? AND created=? AND context=? ORDER BY captured_ms DESC LIMIT 1',(pid,created,context)).fetchone()
  if last and last['state_hash']==digest and last['epoch']==epoch:return digest
  self.db.execute('INSERT OR REPLACE INTO session_states VALUES(?,?,?,?,?,?,?,?,?)',(pid,created,context,epoch,captured_ms,self.branch,self.info()['game_date'],digest,state))
  # Saved checkpoints retain their own complete copy. This rolling journal
  # only bridges busy UI compilation and saves received between helper polls.
  self.db.execute('DELETE FROM session_states WHERE pid=? AND created=? AND captured_ms NOT IN (SELECT captured_ms FROM session_states WHERE pid=? AND created=? ORDER BY captured_ms DESC LIMIT 128)',(pid,created,pid,created))
  return digest
 def one(self,table,key,value):return next(iter(self.rows(table,key+'=?',(value,))),None)
 def active(self,club=None,coach=None):
  key,value=('club_id',club) if club is not None else ('coach_id',coach)
  return next(iter(self.rows('appointments',key+'=? AND end_date IS NULL',(value,))),None)
 def policy(self):return dict(DEFAULTS,**{r['key']:r['value'] for r in self.rows('market_rules')})
 def upgrade_policy(self):
  existing={r['key']:r['value'] for r in self.rows('market_rules')}
  if existing.get('market_policy_version',1)>=2:return
  for key,old,new in (('pressure_threshold',36,32),('max_dismissal_bps',1500,2500)):
   if existing.get(key)==old:self.db.execute('UPDATE market_rules SET value=? WHERE branch=? AND key=?',(new,self.branch,key))
  for key in ('dismissal_slope_bps','market_policy_version'):
   self.db.execute('INSERT OR REPLACE INTO market_rules VALUES(?,?,?)',(self.branch,key,DEFAULTS[key]))
 def import_new_coaches(self):
  present={c['coach_id']:c for c in self.rows('coaches')};db=sqlite3.connect(self.catalog);db.row_factory=sqlite3.Row
  try:
   for c in db.execute('SELECT * FROM coaches'):
    if c['coach_id'] not in present:self.add('coaches',dict(c))
    else:
     fields=('name','nationality','birth_date','style','image','eligible','fictional')
     if any(c[f]!=present[c['coach_id']][f] for f in fields):self.db.execute('UPDATE coaches SET '+','.join(f+'=?' for f in fields)+' WHERE branch=? AND coach_id=?',(*(c[f] for f in fields),self.branch,c['coach_id']))
  finally:db.close()
 def sync_clubs(self,context):
  for c in context.get('clubs',[]):
   old=self.one('clubs','club_id',c['club_id'])
   if old:
    self.db.execute('UPDATE clubs SET league_id=?,league_name=?,name=?,budget=?,reputation=?,country=?,level=? WHERE branch=? AND club_id=?',(c['league_id'],c['league_name'],c['name'],c['budget'],c['reputation'],c['country'] or old['country'],c['level'],self.branch,c['club_id']))
   else:
    self.add('clubs',c)
    # New league/club expansion does not require any hardcoded club IDs.
    cid='GEN-'+str(c['club_id']);self.add('coaches',dict(coach_id=cid,name='Técnico '+c['name'],nationality=c['country'],birth_date=None,reputation=c['reputation'],salary=10000,style='Equilibrado',image='minifaces/NOTFOUND_DEFAULT.png',eligible=1,fictional=1))
    self.appoint(self.one('coaches','coach_id',cid),c,context['date'],'expansion',initial=True)
 def wage(self,coach,club):
  rep=max(1,min(10,coach['reputation']));base=max(3000,min(2500000,club['budget']*.002+rep*rep*2500))
  old=coach['salary'] or base;factor=max(.65,min(1.75,club['reputation']/max(1,rep)))
  return int(round((base*.7+old*.3)*factor/100)*100)
 def future_market(self,today,context,p):
  if not p['enabled']:return
  info=self.info();at=day(today)
  for c in self.rows('coaches'):
   if c['coach_id'].startswith('USER-'):continue
   try:
    born=date.fromisoformat(c['birth_date']);age=at.year-born.year-((at.month,at.day)<(born.month,born.day));retire=age>=p['retirement_age']
   except (ValueError,TypeError):retire=elapsed(info['start_date'],today)>=35*365
   if not retire:continue
   self.db.execute('UPDATE coaches SET eligible=0 WHERE branch=? AND coach_id=?',(self.branch,c['coach_id']))
   a=self.active(coach=c['coach_id'])
   if a and a['club_id']!=context['club']:self.leave(a,today,'retirement','Encerramento da carreira de treinador')
  if not p['regens_enabled']:return
  employed={a['coach_id'] for a in self.rows('appointments','end_date IS NULL')};free=[c for c in self.rows('coaches','eligible=1') if c['coach_id'] not in employed];clubs=self.rows('clubs');vacant=sum(not self.active(club=c['club_id']) for c in clubs)
  needed=max(0,int(p['minimum_free_coaches'])+vacant-len(free))
  if not needed or not clubs:return
  first=('Lucas','Daniel','Rafael','Alex','Bruno','Martin','Nicolas','André','David','Miguel','Paulo','Leonardo');last=('Silva','Costa','Martin','Santos','Almeida','Ribeiro','Mendes','Moreira','Souza','Andrade','Castro','Ferreira')
  for n in range(needed):
   index=draw(info['seed'],'regen',today,n);club=clubs[index%len(clubs)];ident='REGEN-'+str(today)+'-'+str(n);age=30+index%13
   if self.one('coaches','coach_id',ident):continue
   self.add('coaches',dict(coach_id=ident,name=first[index%len(first)]+' '+last[(index//len(first))%len(last)],nationality=club['country'],birth_date=f'{at.year-age}-01-01',reputation=3+index%4,salary=30000+index%6*10000,style=('Equilibrado','Posse de bola','Transições rápidas','Pressão alta')[index%4],image='minifaces/NOTFOUND_DEFAULT.png',eligible=1,fictional=1))
 def appoint(self,coach,club,today,kind,initial=False,started=None):
  if self.active(club=club['club_id']) or self.active(coach=coach['coach_id']):raise ValueError('Nomeação duplicada')
  p=self.policy();salary=self.wage(coach,club);ident=uuid.uuid4().hex
  self.add('appointments',dict(id=ident,coach_id=coach['coach_id'],club_id=club['club_id'],start_date=started or today,end_date=None,end_reason=None,monthly_wage=salary,contract_end=after_months(today,int(p['contract_months'])),origin='Vínculo inicial desde o início da carreira' if initial and started else 'Estimado a partir da ativação do mod' if initial else 'Mercado simulado'))
  if not initial:
   for row in self.rows('performance_evidence','club_id=?',(club['club_id'],)):
    self.add('appointment_baselines',dict(appointment=ident,season=row['season'],competition_key=row['competition_key'],played=sum(row[k] for k in ('hw','hd','hl','aw','ad','al'))))
  self.db.execute('UPDATE coaches SET salary=? WHERE branch=? AND coach_id=?',(salary,self.branch,coach['coach_id']))
  if not initial:self.add('movements',dict(id=ident,game_date=today,coach_id=coach['coach_id'],club_id=club['club_id'],from_club=None,to_club=club['club_id'],kind=kind,reason='Novo projeto e compatibilidade de reputação',old_salary=coach['salary'],new_salary=salary,pressure=0))
 def leave(self,appointment,today,kind,reason,pressure=0,to_club=None):
  if appointment['club_id']==self.info()['user_club'] and kind in ('dismissal','resignation','poached','retirement','renewed'):return False
  self.db.execute('UPDATE appointments SET end_date=?,end_reason=? WHERE branch=? AND id=?',(today,kind,self.branch,appointment['id']))
  self.add('movements',dict(id=uuid.uuid4().hex,game_date=today,coach_id=appointment['coach_id'],club_id=appointment['club_id'],from_club=appointment['club_id'],to_club=to_club,kind=kind,reason=reason,old_salary=appointment['monthly_wage'],new_salary=0,pressure=pressure))
  if kind=='dismissal':
   amount=int(appointment['monthly_wage']*self.policy()['compensation_months'])
   self.add('salary_events',dict(id='severance:'+appointment['id'],coach_id=appointment['coach_id'],club_id=appointment['club_id'],game_date=today,amount=amount,kind='severance'))
 def ensure_user(self,context,today):
  club=context['club'];ident='USER-'+str(context.get('userid',0));old=self.active(coach=ident)
  if old and old['club_id']==club:
   if context.get('user_wage',0)>0:self.db.execute('UPDATE appointments SET monthly_wage=? WHERE branch=? AND id=?',(round(context['user_wage']*52/12),self.branch,old['id']))
   return
  if not self.one('coaches','coach_id',ident):self.add('coaches',dict(coach_id=ident,name=context.get('user_name') or 'Seu treinador',nationality=context.get('user_nationality',''),birth_date=None,reputation=5,salary=context.get('user_wage',0)*52//12,style='Controlado pelo jogador',image='minifaces/NOTFOUND_DEFAULT.png',eligible=0,fictional=0))
  if old:self.leave(old,today,'user_move','Troca de clube na carreira',to_club=club)
  incumbent=self.active(club=club)
  if incumbent:self.leave(incumbent,today,'user_appointment','Clube assumido pelo jogador')
  target=self.one('clubs','club_id',club)
  if target:
   started=context.get('career_start_date') if old is None and today==self.info()['start_date'] else None
   self.appoint(self.one('coaches','coach_id',ident),target,today,'user_appointment',initial=True,started=started)
   if context.get('user_wage',0)>0:self.db.execute('UPDATE appointments SET monthly_wage=? WHERE branch=? AND coach_id=? AND end_date IS NULL',(round(context['user_wage']*52/12),self.branch,ident))
  self.db.execute('UPDATE branches SET user_club=? WHERE id=?',(club,self.branch))
 def coach_at(self,club,today):
  row=self.appointment_at(club,today);return row['coach_id'] if row else None
 def appointment_at(self,club,today):
  row=self.db.execute('SELECT * FROM appointments WHERE branch=? AND club_id=? AND start_date<=? AND (end_date IS NULL OR end_date>?) ORDER BY start_date DESC LIMIT 1',(self.branch,club,today,today)).fetchone()
  return dict(row) if row else None
 def ingest(self,fixtures,today,baseline=False):
  known={r['match_key'] for r in self.rows('results')};added=[];start=self.info()['start_date']
  for m in sorted(fixtures,key=lambda m:(m['date'],m['id'])):
   if not m['played'] or m['date']>today or m['date']<start or m.get('hg') is None or m.get('ag') is None:continue
   key=f"{m['season']}:{m['root']}:{m['id']}:{m['home']}:{m['away']}"
   if key in known:continue
   ha=None if baseline else self.appointment_at(m['home'],m['date']);aa=None if baseline else self.appointment_at(m['away'],m['date'])
   self.add('results',dict(match_key=key,season=m['season'],root=m['root'],competition_id=m['asset'],stage=m['stage'],game_date=m['date'],home=m['home'],away=m['away'],hg=m['hg'],ag=m['ag'],home_coach=ha['coach_id'] if ha else None,away_coach=aa['coach_id'] if aa else None,home_appointment=ha['id'] if ha else None,away_appointment=aa['id'] if aa else None))
   known.add(key);added.append(m)
  return added
 def stats(self,coach,club=None):
  rows=self.rows('results','(home_coach=? OR away_coach=?)',(coach,coach));home=[];away=[]
  for r in rows:
   if r['home_coach']==coach and (club is None or r['home']==club):home.append((r['hg'],r['ag']))
   if r['away_coach']==coach and (club is None or r['away']==club):away.append((r['ag'],r['hg']))
  return dict(total=score(home+away),home=score(home),away=score(away))
 def table_pressure(self,club,table,today,p):
  if not table or club['club_id'] not in {r['club'] for r in table}:return None
  ranks=sorted(table,key=lambda r:r['rank']);r=next(r for r in ranks if r['club']==club['club_id']);n=len(ranks)
  peers={c['club_id']:c for c in self.rows('clubs')};expected=sorted(ranks,key=lambda r:(-peers.get(r['club'],{}).get('reputation',4),r['club']))
  er=next(i+1 for i,x in enumerate(expected) if x['club']==club['club_id']);gap=max(0,(r['rank']-er)/max(1,n-1));ppg=r['points']/max(1,r['played']);target=2.25-1.35*(er-1)/max(1,n-1)
  recent=self.rows('results','(home=? OR away=?) AND game_date<=?',(club['club_id'],club['club_id'],today))
  recent=sorted(recent,key=lambda r:(r['game_date'],r['match_key']),reverse=True)[:5]
  pts=sum(3 if (x['hg']>x['ag'] if x['home']==club['club_id'] else x['ag']>x['hg']) else 1 if x['hg']==x['ag'] else 0 for x in recent)
  poor=max(0,1-pts/max(1,len(recent)*1.6)) if len(recent)>=3 else 0
  relegation=r['rank']>n-max(2,round(n*.15)) and er<=n*.6
  cup=any(elapsed(x['game_date'],today)<=30 and x['prestige']>=7 for x in self.rows('cup_exits','club_id=? AND game_date<=?',(club['club_id'],today)))
  pressure=gap*p['position_weight']+poor*p['form_weight']+max(0,target-ppg)/2.25*p['points_weight']+relegation*p['relegation_weight']+(p['cup_weight'] if cup and (gap>.12 or ppg<target*.8) else 0)
  reasons=[]
  if gap>.12:reasons.append(f"{r['rank']}º, expectativa de {er}º")
  if poor>.3:reasons.append('sequência recente ruim')
  if relegation:reasons.append('risco de rebaixamento')
  if cup and pressure>=p['pressure_threshold']:reasons.append('eliminação em copa de prestígio')
  return pressure,r['rank'],er,'; '.join(reasons) or 'Desempenho dentro da expectativa'
 def hire(self,club,today,seed):
  if club['club_id']==self.info()['user_club']:return False
  p=self.policy();employed={a['coach_id']:a for a in self.rows('appointments','end_date IS NULL')};candidates=[]
  for c in self.rows('coaches','eligible=1'):
   current=employed.get(c['coach_id']);poach=False
   if current:
    source=self.one('clubs','club_id',current['club_id'])
    if current['club_id']==self.info()['user_club'] or elapsed(current['start_date'],today)<90 or not source or club['reputation']<source['reputation']+1.5:continue
    if self.stats(c['coach_id'],current['club_id'])['total']['percentage']<58:continue
    if draw(seed,'poach',club['club_id'],c['coach_id'],today)>=p['poach_bps']:continue
    poach=True
   last=self.rows('movements','coach_id=? AND kind IN (\'dismissal\',\'resignation\')',(c['coach_id'],))
   if last and elapsed(max(x['game_date'] for x in last),today)<14:continue
   salary=self.wage(c,club)
   if salary*12>max(120000,club['budget']*.3+300000):continue
   stats=self.stats(c['coach_id'])['total'];fit=10-abs(c['reputation']-club['reputation'])*2+min(2,stats['games']/50)*(stats['percentage']-45)/20
   if c['nationality']==club['country']:fit+=.8
   fit+=draw(seed,'fit',today,club['club_id'],c['coach_id'])/10000
   candidates.append((fit,c,current if poach else None))
  if not candidates:
   # Promote an internal interim when the external market has no affordable
   # eligible person. A club still has one coach, without duplicating a person.
   ident='INTERIM-'+str(club['club_id'])+'-'+str(today);coach=self.one('coaches','coach_id',ident)
   if not coach:
    self.add('coaches',dict(coach_id=ident,name='Interino do '+club['name'],nationality=club['country'],birth_date=f'{today//10000-40}-01-01',reputation=max(1,min(4,club['reputation']-2)),salary=1000,style='Comissão técnica',image='minifaces/NOTFOUND_DEFAULT.png',eligible=1,fictional=1));coach=self.one('coaches','coach_id',ident)
   self.appoint(coach,club,today,'interim_appointed');salary=max(1000,min(30000,max(club['budget'],40000)//120))
   self.db.execute("UPDATE appointments SET monthly_wage=?,origin='Interino promovido da comissão técnica' WHERE branch=? AND coach_id=? AND end_date IS NULL",(salary,self.branch,ident));self.db.execute('UPDATE coaches SET salary=? WHERE branch=? AND coach_id=?',(salary,self.branch,ident));self.db.execute('UPDATE movements SET new_salary=? WHERE branch=? AND id=?',(salary,self.branch,self.active(coach=ident)['id']));return True
  _,coach,current=max(candidates,key=lambda x:x[0])
  if current:self.leave(current,today,'poached','Contratado por clube de maior reputação',to_club=club['club_id'])
  self.appoint(coach,club,today,'hired');return True
 def review_global(self,context,p):
  """Review actual aggregate progress where FIFA has not published fixtures.

  Counters are evidence for board decisions only, not invented match records.
  New contracts get baselines, so they never inherit a predecessor's games.
  """
  today=context['date'];info=self.info();changed=set();keys=('hw','hd','hl','aw','ad','al')
  previous={(r['season'],r['competition_key'],r['club_id']):r for r in self.rows('performance_evidence')}
  active={r['club_id']:r for r in self.rows('appointments','end_date IS NULL')}
  baseline={(r['appointment'],r['season'],r['competition_key']):r['played'] for r in self.rows('appointment_baselines')}
  evidence=list(context.get('performance',[]));tenure={}
  for r in evidence:
   club=r['club'];a=active.get(club)
   if not a or r['date']>today:continue
   identity=(r['season'],r['key'],club);old=previous.get(identity);played=sum(r[k] for k in keys)
   if old and r['date']<old['game_date']:continue
   values=tuple(r[k] for k in keys)
   if not old or tuple(old[k] for k in keys)!=values:
    self.db.execute('INSERT OR REPLACE INTO performance_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(self.branch,r['season'],r['key'],club,r['date'],*values,r['source']))
    if played and r['date']==today:changed.add(club)
   bk=(a['id'],r['season'],r['key'])
   if bk not in baseline:
    initial=a['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod')
    start=0 if initial else sum(old[k] for k in keys) if old and old['game_date']>=a['start_date'] else played
    self.add('appointment_baselines',dict(appointment=a['id'],season=r['season'],competition_key=r['key'],played=start));baseline[bk]=start
   # A reset/reseeded counter must establish a fresh baseline, not grant games.
   if played<baseline[bk]:
    self.db.execute('UPDATE appointment_baselines SET played=? WHERE branch=? AND appointment=? AND season=? AND competition_key=?',(played,self.branch,*bk));baseline[bk]=played
   tenure[club]=tenure.get(club,0)+max(0,played-baseline[bk])
  if not p['enabled']:return
  for club in self.rows('clubs'):
   ident=club['club_id'];a=self.active(club=ident)
   if ident==context['club'] or ident==info['user_club'] or ident not in changed or not a:continue
   previous_review=self.one('progress','club_id',ident)
   if previous_review and elapsed(previous_review['last_review'],today)<p['review_gap_days']:continue
   if elapsed(a['start_date'],today)<p['min_tenure_days']:continue
   recorded=len(self.rows('results','game_date>=? AND ((home=? AND home_coach=?) OR (away=? AND away_coach=?))',(a['start_date'],ident,a['coach_id'],ident,a['coach_id'])))
   if max(recorded,tenure.get(ident,0))<p['min_tenure_games']:continue
   lid=str(club['league_id']);table=context.get('club_tables',{}).get(str(ident),context.get('tables',{}).get(lid,[]))
   # Saved-only leagues are evaluated when that save date is observed, never
   # by pretending an old table represents the current unsaved month.
   if context.get('table_dates',{}).get(lid,today)!=today:continue
   evaluated=self.table_pressure(club,table,today,p)
   if not evaluated:continue
   pressure,pos,expected,reason=evaluated;probability=min(p['max_dismissal_bps'],max(0,pressure-p['pressure_threshold'])*p['dismissal_slope_bps']);decision='retained'
   self.db.execute('INSERT OR REPLACE INTO progress VALUES(?,?,?)',(self.branch,ident,today))
   fired=self.rows('movements',"club_id=? AND kind='dismissal' AND game_date BETWEEN ? AND ?",(ident,today//10000*10000+101,today//10000*10000+1231))
   if len(fired)<min(3,p['max_dismissals_year']) and probability and draw(info['seed'],'dismiss',ident,today)<probability:
    self.leave(a,today,'dismissal',reason,pressure);decision='dismissal';self.hire(club,today,info['seed'])
   elif draw(info['seed'],'resign',ident,today)<p['resignation_bps']:
    self.leave(a,today,'resignation','Saída por decisão do treinador',pressure);decision='resignation';self.hire(club,today,info['seed'])
   self.db.execute('INSERT OR REPLACE INTO reviews VALUES(?,?,?,?,?,?,?,?)',(self.branch,ident,today,round(pressure,2),pos,expected,'Classificação agregada · '+reason,decision))
 def advance(self,context):
  today=context['date'];info=self.info()
  if today<info['game_date']:raise ValueError('Data retrocedeu: é necessário restaurar o checkpoint do save')
  self.upgrade_policy();p=self.policy();self.import_new_coaches();self.sync_clubs(context);self.ensure_user(context,today)
  # One-time compatibility for the first catalogue: the user's requested
  # initial tenure starts at the native save's startdate, not the mod install.
  initial_date=context.get('career_start_date')
  if initial_date and initial_date<=info['start_date']:
   day(initial_date)
   self.db.execute("UPDATE appointments SET start_date=?,origin='Vínculo inicial desde o início da carreira' WHERE branch=? AND start_date=? AND origin='Estimado a partir da ativação do mod'",(initial_date,self.branch,info['start_date']))
  for c in context.get('competitions',[]):self.db.execute('INSERT OR IGNORE INTO competition_policies VALUES(?,?,?,?)',(self.branch,c['asset'],c['name'],c['prestige']))
  # Results are applied chronologically so a later appointment cannot inherit
  # earlier games after a multi-day simulation.
  fixtures=context['fixtures'];known={r['match_key'] for r in self.rows('results')}
  unseen=[m for m in fixtures if m['played'] and info['start_date']<=m['date']<=today and f"{m['season']}:{m['root']}:{m['id']}:{m['home']}:{m['away']}" not in known]
  dates=sorted({max(info['game_date'],m['date']) for m in unseen})
  for current in dates:
   self.ingest(fixtures,current)
   for x in context.get('cup_exits',[]):
    if x['date']<=current:
     cp=self.one('competition_policies','competition_id',x.get('asset',0));prestige=cp['prestige'] if cp else x['prestige']
     self.db.execute('INSERT OR IGNORE INTO cup_exits VALUES(?,?,?,?,?)',(self.branch,x['root'],x['club'],x['date'],prestige))
   if not p['enabled']:continue
   clubs=self.rows('clubs');tables=context.get('tables',{})
   for club in clubs:
    ident=club['club_id'];a=self.active(club=ident)
    if ident==context['club']:continue
    if not a:
     self.hire(club,current,info['seed']);continue
    previous=self.one('progress','club_id',ident)
    if previous and elapsed(previous['last_review'],current)<p['review_gap_days']:continue
    if not any(max(info['game_date'],m['date'])==current and ident in (m['home'],m['away']) for m in unseen):continue
    tenure_games=len(self.rows('results','game_date>=? AND ((home=? AND home_coach=?) OR (away=? AND away_coach=?))',(a['start_date'],ident,a['coach_id'],ident,a['coach_id'])))
    if elapsed(a['start_date'],current)<p['min_tenure_days'] or tenure_games<p['min_tenure_games']:continue
    # Standings reconstructed as of this day; a future table cannot leak into
    # a decision during a multi-day jump.
    table=table_for(fixtures,club['league_id'],current,{c['club_id'] for c in clubs if c['league_id']==club['league_id']})
    if not table:table=tables.get(str(club['league_id']),[]) if current==today else []
    evaluated=self.table_pressure(club,table,current,p)
    if not evaluated:continue
    pressure,pos,expected,reason=evaluated;decision='retained'
    self.db.execute('INSERT OR REPLACE INTO progress VALUES(?,?,?)',(self.branch,ident,current))
    fired=self.rows('movements','club_id=? AND kind=\'dismissal\' AND game_date BETWEEN ? AND ?',(ident,current//10000*10000+101,current//10000*10000+1231))
    probability=min(p['max_dismissal_bps'],max(0,pressure-p['pressure_threshold'])*p['dismissal_slope_bps'])
    if len(fired)<min(3,p['max_dismissals_year']) and probability and draw(info['seed'],'dismiss',ident,current)<probability:
     self.leave(a,current,'dismissal',reason,pressure);decision='dismissal';self.hire(club,current,info['seed'])
    elif draw(info['seed'],'resign',ident,current)<p['resignation_bps']:
     self.leave(a,current,'resignation','Saída por decisão do treinador',pressure);decision='resignation';self.hire(club,current,info['seed'])
    self.add('reviews',dict(club_id=ident,game_date=current,pressure=round(pressure,2),position=pos,expected_position=expected,reason=reason,decision=decision))
  self.ingest(fixtures,today)
  self.review_global(context,p)
  for title in context.get('titles',[]):
   if title['date']<info['start_date'] or title['date']>today:continue
   evidence=self.db.execute('SELECT home,home_coach,away_coach FROM results WHERE branch=? AND root=? AND competition_id=? AND game_date<=? AND (home=? OR away=?) ORDER BY game_date DESC LIMIT 1',(self.branch,title['root'],title['asset'],title['date'],title['club'],title['club'])).fetchone()
   coach=(evidence['home_coach'] if evidence['home']==title['club'] else evidence['away_coach']) if evidence else None
   if coach:
    inserted=self.db.execute('INSERT OR IGNORE INTO honours VALUES(?,?,?,?,?,?,?,?)',(self.branch,coach,title['club'],title['season'],title['asset'],title['root'],title['date'],title['name'])).rowcount
    if inserted:self.db.execute('UPDATE coaches SET reputation=MIN(10,reputation+.25) WHERE branch=? AND coach_id=?',(self.branch,coach))
  self.future_market(today,context,p)
  # Every vacant club receives a replacement, including a club whose coach was
  # poached later in the day's review order.
  if p['enabled']:
   for club in self.rows('clubs'):
    if club['club_id']!=context['club'] and not self.active(club=club['club_id']):self.hire(club,today,info['seed'])
  # CPU salary ledger is simulated in this database. The user's native wage
  # remains owned by the existing finance bridge, preventing double charges.
  from calendar import monthrange
  cursor=day(info['game_date']).replace(day=1);end=day(today)
  while cursor<=end:
   last=cursor.replace(day=monthrange(cursor.year,cursor.month)[1]);due=packed(last)
   if info['game_date']<due<=today:
    for a in self.rows('appointments','start_date<=? AND (end_date IS NULL OR end_date>=?)',(due,packed(cursor))):
     if a['club_id']==context['club']:continue
     first=max(day(a['start_date']),cursor);finish=min(day(a['end_date'])-timedelta(days=1) if a['end_date'] else last,last)
     if finish<first:continue
     amount=round(a['monthly_wage']*((finish-first).days+1)/last.day)
     self.db.execute('INSERT OR IGNORE INTO salary_events VALUES(?,?,?,?,?,?,?)',(self.branch,'salary:'+a['id']+':'+str(due),a['coach_id'],a['club_id'],due,amount,'salary'))
   cursor=(last+timedelta(days=1)).replace(day=1)
  # Contract renewals change the new term only; salaries never rewrite old terms.
  for a in self.rows('appointments','end_date IS NULL AND contract_end<=?',(today,)):
   if not p['enabled'] or a['club_id']==context['club']:continue
   coach=self.one('coaches','coach_id',a['coach_id']);club=self.one('clubs','club_id',a['club_id']);stats=self.stats(coach['coach_id'],club['club_id'])['total'];delta=max(-.5,min(.5,(stats['percentage']-45)/35)) if stats['games']>=10 else 0
   self.db.execute('UPDATE coaches SET reputation=? WHERE branch=? AND coach_id=?',(max(1,min(10,coach['reputation']+delta)),self.branch,coach['coach_id']))
   self.leave(a,today,'renewed','Renovação do contrato');self.appoint(self.one('coaches','coach_id',coach['coach_id']),club,today,'renewal')
  self.db.execute('UPDATE branches SET game_date=?,season=? WHERE id=?',(today,context['season'],self.branch))

def table_for(fixtures,asset,today,members):
 matches=[m for m in fixtures if m['asset']==asset and m['played'] and m['date']<=today and m['home'] in members and m['away'] in members and m.get('hg') is not None]
 if not matches:return []
 rows={t:dict(club=t,played=0,points=0,gf=0,ga=0) for t in members}
 for m in matches:
  for t,gf,ga in ((m['home'],m['hg'],m['ag']),(m['away'],m['ag'],m['hg'])):
   r=rows[t];r['played']+=1;r['points']+=3 if gf>ga else 1 if gf==ga else 0;r['gf']+=gf;r['ga']+=ga
 result=sorted(rows.values(),key=lambda r:(-r['points'],-(r['gf']-r['ga']),-r['gf'],r['club']))
 for i,r in enumerate(result):r['rank']=i+1
 return result
