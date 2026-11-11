"""Join saved career metadata with the verified owner-thread FCE publication."""
from pathlib import Path
import hashlib,json,sys

class Inputs:
 def __init__(self,game):
  self.game=Path(game);sys.path.insert(0,str(self.game/'ModCarrerMode/source/club_browser'))
  from lineup_data import ProjectionCache
  self.cache=ProjectionCache()
 def read(self,observed,memory=None,offline=False,live_leagues=None,league_only=False,calendar_snapshot=None):
  from competition_schedule import read_schedule
  from competition_formats import read_formats
  from engine import table_for
  game=self.game;saved=observed['save'];today=observed['date'];path=Path(saved['path']);before=path.stat();raw,dbs,base=self.cache.load(game,path)
  def rows(name,fields):
   found=[d for d in dbs if name in d.tables];db=found[0] if found else base
   if len(found)>1:raise ValueError('Tabela ambígua: '+name)
   if name not in db.tables:return []
   available=db.tables[name]['fields'];return db.rows(name,[f for f in fields if f in available])
  calendar=rows('career_calendar',['startdate','currdate']);users=rows('career_users',['userid','clubteamid','firstname','surname','nationalteamid','seasoncount']);user=users[0] if len(users)==1 else {}
  from derived_campaigns import augment
  if calendar_snapshot is not None:
   if calendar_snapshot.get('date')!=today:raise ValueError('Campanha de outra data')
   snapshot=dict(calendar_snapshot,source='live_calendar')
  elif league_only:
   if memory is None or live_leagues is None or live_leagues['date']!=today:raise ValueError('Aguardando ligas nativas da data atual')
   # The verified owner-thread league rows are enough for daily board reviews.
   # Keep dated scores from DATA as saved evidence; never relabel an old FCE
   # graph, synthesize goals or wait for the full competition graph to open UI.
   snapshot=dict(date=today,nodes=[],fixtures=[],standings=[],stats=[],source='live_league_only')
  else:
   from saved_competitions import read as read_saved_competitions
   snapshot=augment(game,path,raw,read_saved_competitions(raw,calendar[0]['currdate']),today,saved.get('pid'),saved.get('process_created_100ns'),observed['profile'].get('context_epoch'))
  if memory is not None and snapshot.get('source') not in ('save_bound_native','live_league_only','live_calendar'):raise ValueError('Aguardando publicação consistente da carreira em RAM')
  season=calendar[0]['startdate'];formats=read_formats(game)
  from title_evidence import career_start,merge_scores,completed_titles
  title_start=career_start(calendar[0],user)
  fixtures=merge_scores(read_schedule(raw,formats),snapshot,title_start)
  result=[]
  for m in fixtures:
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
  global_data=global_projection(snapshot,result,memberships,league_links,today if live_leagues else calendar[0]['currdate'],season,snapshot['date'],'live_league' if live_leagues else 'saved_league')
  for row in global_data['performance']:
   if row['source']=='fce':row['source']='native_view' if snapshot.get('source') in ('save_bound_native','live_calendar') else 'saved_fce'
  global_data['coverage'].update(live_competitions=global_data['coverage'].get('competitions',0) if snapshot.get('source') in ('save_bound_native','live_league_only') else 0,live_league_tables=len({r['leagueid'] for r in league_links}) if live_leagues else 0,live_database=live_leagues is not None,league_only=league_only)
  global_data['coverage'].update(derived_campaigns=len(snapshot.get('derived_slots',[])),native_bound=snapshot.get('source')=='save_bound_native')
  tables.update(global_data['tables'])
  titles=[];exits=[];competition_profiles={}
  from competition_labels import resolve as competition_label
  comp_name=lambda asset:competition_label(game,asset,league_defs.get(asset,{}).get('leaguename',''))
  for asset in {m['asset'] for m in result}:
   participants={m[t] for m in result if m['asset']==asset for t in ('home','away')};reps=[c['reputation'] for c in clubs if c['club_id'] in participants];league_count=len({c['league_id'] for c in clubs if c['club_id'] in participants})
   competition_profiles[asset]=dict(asset=asset,name=comp_name(asset),prestige=max(1,min(10,round((sum(reps)/len(reps) if reps else 4)+(2 if league_count>1 else 0)))))
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
  evidence=fixtures
  leagues={int(lid):dict(members={c['club_id'] for c in clubs if c['league_id']==int(lid)}) for lid in tables}
  titles=[dict(t,asset=t['competition']) for t in completed_titles(evidence,formats,leagues,today,title_start,comp_name)]
  managers=rows('career_managerinfo',['userid','clubteamid','wage','boardconfidence','internationalteamid']);user_manager=next((r for r in managers if r.get('userid')==user.get('userid') and r.get('clubteamid')==observed['profile']['club_id']),{});wage=user_manager.get('wage',0)
  from national_title_context import observations
  national_teams={r['teamid'] for r in base.rows('teamnationlinks',['teamid'])}
  national_jobs=observations(user,user_manager,calendar[0]['currdate'],today,national_teams,memory,observed['profile'])
  if path.stat().st_mtime_ns!=before.st_mtime_ns:raise ValueError('Save alterado durante leitura dos técnicos')
  return dict(title_start=title_start,title_fixtures=evidence,national_teams=sorted(national_teams),national_jobs=national_jobs,title_formats=formats,title_labels={m['asset']:comp_name(m['asset']) for m in fixtures},club=observed['profile']['club_id'],saved_club=user.get('clubteamid',observed['profile']['club_id']),saved_date=calendar[0]['currdate'],career_start_date=calendar[0]['startdate'],userid=user.get('userid',0),user_name=' '.join(str(user.get(k) or '') for k in ('firstname','surname')).strip(),user_wage=wage,user_confidence=user_manager.get('boardconfidence'),date=today,season=season,clubs=clubs,fixtures=result,tables=tables,club_tables=global_data['club_tables'],performance=global_data['performance'],table_dates=global_data['table_dates'],coverage=global_data['coverage'],titles=titles,cup_exits=exits,competitions=list(competition_profiles.values()),digest=hashlib.sha256(raw).hexdigest())
