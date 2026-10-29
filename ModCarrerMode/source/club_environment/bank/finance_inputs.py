"""Validated read-only facts for club finance, reusing the competition readers."""
from pathlib import Path
import csv,json,sys
from club_finance import median_value

class FinanceInputs:
 def __init__(self,game):
  self.game=Path(game)
  sys.path.insert(0,str(self.game/'ModCarrerMode/source/club_browser'))
  self.cache=None;self.last_signature=None;self.last=None;self.details_signature=None;self.details={}

 def read(self,save,live,*,pid,userid,created=None):
  game=self.game;save=Path(save)
  snapshot=json.loads((game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'))
  same_path=Path(snapshot.get('savePath','')).resolve()==save.resolve()
  if (snapshot.get('schema')!=3 or snapshot.get('pid')!=pid or snapshot.get('club')!=live['club']
      or snapshot.get('date')!=live['date'] or not same_path
      or (created is not None and snapshot.get('processCreated100ns')!=created)):
   raise ValueError('Aguardando dados atuais das competições desta carreira')
  signature=(save.stat().st_mtime_ns,save.stat().st_size,live['club'],live['date'],snapshot.get('generation'),
    tuple(tuple(f) for f in snapshot['fixtures']))
  if signature==self.last_signature:return self.last
  if self.cache is None:
   from lineup_data import ProjectionCache
   self.cache=ProjectionCache()
  raw,dbs,base=self.cache.load(game,save)
  def rows(name,fields,base_only=False):
   found=[d for d in dbs if name in d.tables]
   db=base if base_only or not found else found[0]
   if name not in db.tables:return []
   return db.rows(name,fields)
  from competition_schedule import read_schedule,read_assignment_roots
  from competition_formats import read_formats
  formats=read_formats(game);fixtures={m['id']:m for m in read_schedule(raw,formats)}
  nodes={n[0]:n for n in snapshot['nodes']}
  def root(ident):
   seen=set()
   while ident in nodes and ident not in seen:
    seen.add(ident);n=nodes[ident]
    if n[2]==3:return n[0],n[3]
    ident=n[1]
   return None
  club=live['club'];roots={r['root']:r['asset'] for r in read_assignment_roots(raw).get(club,[])}
  for f in snapshot['fixtures']:
   ident=root(f[1])
   if len(f)<10 or not ident or f[5]<=0 or f[6]<=0 or f[5]==f[6]:continue
   old=fixtures.get(f[0]);stage=old['stage'] if old and (old['home'],old['away'],old['root'])==(f[5],f[6],ident[0]) else f[2]
   fixtures[f[0]]=dict(id=f[0],root=ident[0],asset=ident[1],date=f[3],home=f[5],away=f[6],
    played=f[9]==1 and 0<=f[7]<100 and 0<=f[8]<100,stage=stage)
   if club in f[5:7]:roots[ident[0]]=ident[1]
  calendar=rows('career_calendar',['currdate','startdate'])
  if len(calendar)!=1:raise ValueError('Calendário financeiro ambíguo')
  season=calendar[0]['startdate']
  # FCE publication identifies the active session, while saved tables provide
  # immutable metadata only. Never reuse another club's manager remuneration.
  managers=[r for r in rows('career_managerinfo',['userid','clubteamid','wage']) if r['userid']==userid and r['clubteamid']==club]
  wage=managers[0]['wage'] if len(managers)==1 and 0<=managers[0]['wage']<100_000_000 else None
  teams={r['teamid']:r for r in rows('teams',['teamid','teamname','transferbudget','domesticprestige'])}
  original={r['teamid']:r for r in rows('teams',['teamid','teamname','transferbudget','domesticprestige'],True)}
  leagues={r['leagueid']:r for r in rows('leagues',['leagueid','leaguename','level'],True)}
  links=rows('leagueteamlinks',['teamid','leagueid'])
  labels={k:r['leaguename'] for k,r in leagues.items()}
  try:
   for line in (game/'ModCarrerMode/data/club_browser/catalog.tsv').read_text(encoding='utf-8-sig').splitlines():
    r=line.split('\t')
    if len(r)==18:labels[int(r[5])]=r[6]
   state=json.loads((game/'ModCarrerMode/runtime/club_environment/preview/runtime/competition_labels_r57.json').read_text(encoding='utf8'))
   for key,value in state.get('names',{}).items():
    for prefix in ('TrophyName_','TrophyName_Abbr15_','LeagueName_'):
     if key.startswith(prefix) and key[len(prefix):].isdigit() and value and '\ufffd' not in value:labels[int(key[len(prefix):])]=value
  except (OSError,ValueError):pass
  neutral=set()
  for r in csv.reader((game/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/settings.txt').read_text(encoding='utf-8-sig').splitlines()):
   if len(r)==3 and r[0].isdigit() and r[1]=='match_stadium':neutral.add(int(r[0]))
  own=[]
  for m in fixtures.values():
   if club not in (m['home'],m['away']) or m['date']<season:continue
   ident=m['stage'];seen=set();fixed=False
   while ident in nodes and ident not in seen:
    seen.add(ident);fixed|=ident in neutral;ident=nodes[ident][1]
   m=dict(m,neutral=bool(fixed or m['root'] in neutral),home_name=teams.get(m['home'],{}).get('teamname','Clube '+str(m['home'])),
    away_name=teams.get(m['away'],{}).get('teamname','Clube '+str(m['away'])));own.append(m);roots[m['root']]=m['asset']
  profiles=[]
  for ident,asset in roots.items():
   participants={r['teamid'] for r in links if r['leagueid']==asset}
   if not participants:
    for m in fixtures.values():
     if m['root']==ident:participants.update((m['home'],m['away']))
   reference=[original.get(t,teams.get(t,{})) for t in participants]
   budgets=[t['transferbudget'] for t in reference if t.get('transferbudget',0)>0]
   prestige=[t['domesticprestige'] for t in reference if t.get('domesticprestige',0)>0]
   profiles.append(dict(root=ident,asset=asset,name=labels.get(asset,'Competição '+str(asset)),
    budgets=budgets,prestige=median_value(prestige) if prestige else 5,level=leagues.get(asset,{}).get('level',1)))
  stadium_links=[r['stadiumid'] for r in rows('teamstadiumlinks',['teamid','stadiumid']) if r['teamid']==club]
  stadium=[r for r in rows('stadiums',['stadiumid','name','capacity']) if len(set(stadium_links))==1 and r['stadiumid']==stadium_links[0]]
  capacity=stadium[0]['capacity'] if len(stadium)==1 else 0
  preferences=[r for r in rows('career_managerpref',['managerprefid','startofseasontransferbudget']) if r['managerprefid']==userid]
  members={r['playerid'] for r in rows('teamplayerlinks',['teamid','playerid']) if r['teamid']==club}
  contracts=[r for r in rows('career_playercontract',['teamid','playerid','wage']) if r['teamid']==club and r['playerid'] in members]
  payroll=sum(r['wage'] for r in contracts) if len(contracts)==len(members)==len({r['playerid'] for r in contracts}) and members else None
  result=dict(club=club,club_name=teams.get(club,{}).get('teamname','Clube'),date=live['date'],season=season,
   coach_wage=wage,capacity=capacity,competitions=profiles,fixtures=own,player_weekly=payroll,
   budget_initial=preferences[0]['startofseasontransferbudget'] if len(preferences)==1 else None)
  club_reference=original.get(club,teams.get(club,{}))
  result['club_profile']=dict(base_budget=club_reference.get('transferbudget',0),prestige=club_reference.get('domesticprestige',5))
  # Optional views never gate the financial clock. Cache save-backed roster
  # metadata independently from the frequently published live fixture snapshot.
  detail_signature=signature[:3]
  if detail_signature!=self.details_signature:
   self.details=dict(players=[],transfers=[],player_error=None,transfer_error=None)
   from finance_people import payroll_rows,club_transfers
   try:
    from roster_data import project
    roster=project(game,save,club,cache=self.cache,season=snapshot)['players']
    ids={p['id'] for p in roster}
    expiry={r['playerid']:r['contractvaliduntil'] for r in self.cache.matching(base,'players',['playerid','contractvaliduntil'],'playerid',ids)}
    for db in dbs:
     if 'players' in db.tables:
      expiry.update({r['playerid']:r['contractvaliduntil'] for r in self.cache.matching(db,'players',['playerid','contractvaliduntil'],'playerid',ids) if r['contractvaliduntil'] is not None})
    self.details['players']=payroll_rows(roster,contracts,expiry)
   except (OSError,ValueError,KeyError,ImportError) as error:self.details['player_error']=str(error)
   try:
    from read_market import read_snapshot
    market=read_snapshot(game,save,club_override=club,date_override=live['date'])
    self.details['transfers']=club_transfers(market,club,season,live['date'])
   except (OSError,ValueError,KeyError,ImportError) as error:self.details['transfer_error']=str(error)
   self.details_signature=detail_signature
  result.update(self.details)
  self.last_signature=signature;self.last=result
  return result
