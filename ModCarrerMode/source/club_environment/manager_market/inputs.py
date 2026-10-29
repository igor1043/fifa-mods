"""Join saved career metadata with the verified owner-thread FCE publication."""
from pathlib import Path
import hashlib,json,sys

class Inputs:
 def __init__(self,game):
  self.game=Path(game);sys.path.insert(0,str(self.game/'ModCarrerMode/source/club_browser'))
  from lineup_data import ProjectionCache
  self.cache=ProjectionCache()
 def read(self,observed,memory=None,offline=False,live_leagues=None):
  from competition_schedule import read_schedule
  from competition_formats import read_formats
  from engine import table_for
  game=self.game;saved=observed['save'];today=observed['date'];path=Path(saved['path']);before=path.stat();raw,dbs,base=self.cache.load(game,path)
  snapshot=json.loads((game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'))
  if not offline:
   from season_stats import current
   snapshot=current(game,memory,saved,observed['profile'])
   if snapshot is None:raise ValueError('Aguardando resultados atuais desta carreira')
  if Path(snapshot['savePath']).resolve()!=path.resolve() or snapshot['date']!=today:raise ValueError('Resultados de outra carreira ou data')
  def rows(name,fields):
   found=[d for d in dbs if name in d.tables];db=found[0] if found else base
   if len(found)>1:raise ValueError('Tabela ambígua: '+name)
   if name not in db.tables:return []
   available=db.tables[name]['fields'];return db.rows(name,[f for f in fields if f in available])
  calendar=rows('career_calendar',['startdate','currdate']);users=rows('career_users',['userid','clubteamid','firstname','surname']);user=users[0] if len(users)==1 else {}
  season=calendar[0]['startdate'];formats=read_formats(game);fixtures={m['id']:m for m in read_schedule(raw,formats)};nodes={r[0]:r for r in snapshot['nodes']}
  def root(n):
   seen=set()
   while n in nodes and n not in seen:
    seen.add(n);r=nodes[n]
    if r[2]==3:return r[0],r[3]
    n=r[1]
   return None
  for f in snapshot['fixtures']:
   if len(f)<10:continue
   comp=root(f[1])
   if not comp:continue
   old=fixtures.get(f[0]);stage=old['stage'] if old and (old['home'],old['away'],old['root'])==(f[5],f[6],comp[0]) else f[2]
   fixtures[f[0]]=dict(id=f[0],root=comp[0],asset=comp[1],stage=stage,stageKind=formats.get(stage,{}).get('kind',old.get('stageKind',0) if old else 0),date=f[3],home=f[5],away=f[6],homeScore=f[7] if f[9]==1 else None,awayScore=f[8] if f[9]==1 else None,played=f[9]==1)
  result=[]
  for m in fixtures.values():
   if m['date']<season or m['home']<=0 or m['away']<=0 or m['home']==m['away']:continue
   hg,ag=m.get('homeScore'),m.get('awayScore');played=bool(m['played'] and hg is not None and ag is not None and 0<=hg<100 and 0<=ag<100)
   result.append(dict(id=m['id'],root=m['root'],asset=m['asset'],stage=m['stage'],kind=m.get('stageKind',0),date=m['date'],home=m['home'],away=m['away'],hg=hg,ag=ag,played=played,season=season))
  from catalog_meta import populate,Labels
  populate(game/'ModCarrerMode/data/manager_market/catalog.sqlite3',base,game/'ModCarrerMode/data/club_browser/catalog.tsv')
  labels=Labels(game/'ModCarrerMode/data/manager_market/catalog.sqlite3')
  league_links=rows('leagueteamlinks',['teamid','leagueid','secondarytable','homewins','homedraws','homelosses','awaywins','awaydraws','awaylosses','nummatchesplayed','points','homegf','homega','awaygf','awayga'])
  if live_leagues is not None:league_links=live_leagues['rows']
  league_defs={r['leagueid']:r for r in base.rows('leagues',['leagueid','leaguename','countryid','level'])};memberships={r['teamid']:r['leagueid'] for r in league_links if r.get('secondarytable')==0 and league_defs.get(r['leagueid'],{}).get('level',0)>0}
  clubs=[]
  for r in rows('teams',['teamid','teamname','domesticprestige','transferbudget']):
   if r['teamid'] not in memberships:continue
   lid=memberships[r['teamid']];definition=labels.leagues.get(lid,{});country=labels.countries.get(definition.get('country_id',league_defs[lid]['countryid']),{}).get('name','')
   clubs.append(dict(club_id=r['teamid'],name=r['teamname'],league_id=lid,league_name=definition.get('name',league_defs[lid]['leaguename']),country=country,region='Outras regiões',reputation=max(1,min(10,(r.get('domesticprestige') or 8)/2)),budget=max(0,r.get('transferbudget') or 1000000),level=league_defs[lid]['level']))
  tables={str(lid):table_for(result,lid,today,{r['club_id'] for r in clubs if r['league_id']==lid}) for lid in set(memberships.values())}
  from global_performance import project as global_projection
  global_data=global_projection(snapshot,result,memberships,league_links,today if live_leagues is not None else calendar[0]['currdate'],season,today,'live_league' if live_leagues is not None else 'saved_league')
  tables.update(global_data['tables'])
  titles=[];exits=[];competition_profiles={}
  for asset in {m['asset'] for m in result}:
   participants={m[t] for m in result if m['asset']==asset for t in ('home','away')};reps=[c['reputation'] for c in clubs if c['club_id'] in participants];league_count=len({c['league_id'] for c in clubs if c['club_id'] in participants})
   competition_profiles[asset]=dict(asset=asset,name=league_defs.get(asset,{}).get('leaguename','Competição '+str(asset)),prestige=max(1,min(10,round((sum(reps)/len(reps) if reps else 4)+(2 if league_count>1 else 0)))))
  # Actual aggregate winners only. Tied aggregates without penalty evidence are
  # deliberately unresolved; titles must never be guessed from a random draw.
  ties={}
  for m in result:
   if m['kind']>=5 and m['kind']!=9:ties.setdefault((m['root'],m['stage'],*sorted((m['home'],m['away']))),[]).append(m)
  for (rt,stage,a,b),legs in ties.items():
   expected=2 if formats.get(stage,{}).get('mode')=='KO2LEGS' else 1
   if len(legs)<expected or not all(m['played'] and m['date']<=today for m in legs):continue
   ga=sum(m['hg'] if m['home']==a else m['ag'] for m in legs);gb=sum(m['hg'] if m['home']==b else m['ag'] for m in legs)
   if ga==gb:continue
   win,lose=(a,b) if ga>gb else (b,a);last=max(m['date'] for m in legs);asset=legs[0]['asset']
   participants={m[t] for m in result if m['root']==rt for t in ('home','away')};reps=[c['reputation'] for c in clubs if c['club_id'] in participants];league_count=len({c['league_id'] for c in clubs if c['club_id'] in participants})
   prestige=max(1,min(10,round((sum(reps)/len(reps) if reps else 4)+(2 if league_count>1 else 0))))
   exits.append(dict(root=rt,asset=asset,club=lose,date=last,prestige=prestige))
   if legs[0]['kind']==10:titles.append(dict(root=rt,asset=asset,club=win,date=last,season=season,name=league_defs.get(asset,{}).get('leaguename','Competição '+str(asset))))
  for lid,table in tables.items():
   matches=[m for m in result if m['asset']==int(lid)];members={r['club'] for r in table}
   if len(members)>=4 and matches and all(m['played'] and m['date']<=today for m in matches) and min((r['played'] for r in table),default=0)>=len(members)-1:
    titles.append(dict(root=matches[0]['root'],asset=int(lid),club=table[0]['club'],date=max(m['date'] for m in matches),season=season,name=league_defs[int(lid)]['leaguename']))
  managers=rows('career_managerinfo',['userid','clubteamid','wage','boardconfidence']);user_manager=next((r for r in managers if r.get('userid')==user.get('userid') and r.get('clubteamid')==observed['profile']['club_id']),{});wage=user_manager.get('wage',0)
  if path.stat().st_mtime_ns!=before.st_mtime_ns:raise ValueError('Save alterado durante leitura dos técnicos')
  return dict(club=observed['profile']['club_id'],saved_club=user.get('clubteamid',observed['profile']['club_id']),saved_date=calendar[0]['currdate'],career_start_date=calendar[0]['startdate'],userid=user.get('userid',0),user_name=' '.join(str(user.get(k) or '') for k in ('firstname','surname')).strip(),user_wage=wage,user_confidence=user_manager.get('boardconfidence'),date=today,season=season,clubs=clubs,fixtures=result,tables=tables,club_tables=global_data['club_tables'],performance=global_data['performance'],table_dates=global_data['table_dates'],coverage=global_data['coverage'],titles=titles,cup_exits=exits,competitions=list(competition_profiles.values()),digest=hashlib.sha256(raw).hexdigest())
