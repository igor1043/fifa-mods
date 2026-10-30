"""Read-only coach profile, scoped by selected club and validated active career.

Club results are never presented as a coach's lifetime record. User statistics
require an exact userid/club join; another club cannot inherit the user's wage.
"""
from pathlib import Path
import struct,json,sqlite3
from lineup_data import ProjectionCache

KEYS=('games','wins','draws','losses','goalsFor','goalsAgainst','points')

def clean(value):
 return str(value if value is not None else '—').replace('\t',' ').replace('\r',' ').replace('\n',' ').strip()[:180] or '—'

def catalog(path):
 try:
  raw=Path(path).read_bytes()
  try:text=raw.decode('utf-8-sig')
  except UnicodeDecodeError:text=raw.decode('cp1252')
  return [line.split('|') for line in text.splitlines() if line.strip() and not line.startswith('#')]
 except OSError:return []

def manager_for(club,managers,users,info):
 rows=[r for r in managers if r.get('teamid')==club]
 result=dict(rows[0]) if len(rows)==1 else {}
 users=[r for r in users if r.get('clubteamid')==club and r.get('usertype')==1]
 if len(users)==1:
  u=users[0];matches=[r for r in info if r.get('userid')==u.get('userid') and r.get('clubteamid')==club]
  if len(matches)==1:result.update(u);result.update(matches[0])
 return result

def record(matches):
 s=dict.fromkeys(KEYS,0)
 for r in matches:
  gf,ga=r['gf'],r['ga'];s['games']+=1;s['wins']+=gf>ga;s['draws']+=gf==ga;s['losses']+=gf<ga;s['goalsFor']+=gf;s['goalsAgainst']+=ga
 s['points']=s['wins']*3+s['draws'];return s

def season(snapshot,club,leagues,include=None):
 if not snapshot:return {},[],''
 today=snapshot['date'];nodes={r[0]:r for r in snapshot.get('nodes',[]) if len(r)==5};matches={};groups={}
 def root(key):
  seen=set()
  while key in nodes and key not in seen:
   seen.add(key);n=nodes[key]
   if n[2]==3:return n[0],n[3]
   key=n[1]
  return None
 for r in snapshot.get('fixtures',[]):
  if len(r)<10 or any(type(v)!=int for v in r[:10]) or club not in r[5:7] or r[5]==r[6]:continue
  comp=root(r[1])
  if not comp:continue
  group=groups.setdefault(comp,dict(asset=comp[1],name=leagues.get(comp[1],'Competição'),upcoming=False,matches=[]))
  if not r[9]:
   if r[3]>=today:group['upcoming']=True
   continue
  if not 20080101<=r[3]<=today or not all(0<=v<=255 for v in r[7:9]):continue
  if r[0] in matches:
   if matches[r[0]]['raw']!=tuple(r):raise ValueError('Resultados conflitantes da carreira.')
   continue
  home=r[5]==club;m=dict(raw=tuple(r),root=comp[0],date=r[3],id=r[0],home=home,home_club=r[5],away_club=r[6],gf=r[7 if home else 8],ga=r[8 if home else 7]);matches[r[0]]=m
  if include is None or include(m):group['matches'].append(m)
 values=[m for m in matches.values() if include is None or include(m)];s=record(values);s['home']=record([r for r in values if r['home']]);s['away']=record([r for r in values if not r['home']])
 competitions=[]
 for _,g in sorted(groups.items()):
  competitions.append(dict(asset=g['asset'],name=g['name'],**record(g['matches']),status='Em andamento' if g['upcoming'] and g['matches'] else 'A disputar' if g['upcoming'] else 'Resultados registrados'))
 form=''.join('V' if r['gf']>r['ga'] else 'E' if r['gf']==r['ga'] else 'D' for r in sorted(values,key=lambda r:(r['date'],r['id']),reverse=True)[:5])
 return s,competitions,form

def tenure(market,snapshot,club):
 """Confirmed SQL ownership wins over a date interval, especially on hire day."""
 if not market:return {},''
 ids=set(market['appointments']);start=market['start'];today=snapshot['date'] if snapshot else 99991231;known={};matches={}
 def key(r):return r['root'],r['id'],r['home_club'],r['away_club'],r['date']
 for r in market['results']:
  try:_,root,ident,home,away=map(int,r['match_key'].split(':'))
  except (ValueError,KeyError):continue
  own=r['home']==club;m=dict(root=root,id=ident,home_club=home,away_club=away,date=r['game_date'],home=own,gf=r['hg'] if own else r['ag'],ga=r['ag'] if own else r['hg'])
  if not start<=m['date']<=today:continue
  owner=r.get('home_appointment' if own else 'away_appointment');known[key(m)]=owner
  if owner in ids:matches[key(m)]=m
 def include(m):
  k=key(m)
  if not start<=m['date']<=today:return False
  if known.get(k) is not None:allowed=known[k] in ids
  else:allowed=m['date']>start or market['initial']
  if allowed:matches[k]=m
  return allowed
 if snapshot:season(snapshot,club,{},include)
 values=list(matches.values());s=record(values);s['home']=record([r for r in values if r['home']]);s['away']=record([r for r in values if not r['home']])
 form=''.join('V' if r['gf']>r['ga'] else 'E' if r['gf']==r['ga'] else 'D' for r in sorted(values,key=lambda r:(r['date'],r['id']),reverse=True)[:5])
 return s,form

def apply_results(data,evidence,leagues):
 """The team campaign includes simulated leagues with no individual scores."""
 from career_results import club_stats
 data['stats']=club_stats(evidence,data['club'])
 existing={r['asset']:r for r in data['competitions']}
 for row in evidence['summaries']:
  if row['club']!=data['club'] or not row['games']:continue
  old=existing.get(row['asset'],{})
  existing[row['asset']]=dict(asset=row['asset'],name=leagues.get(row['asset'],old.get('name','Competição')),**{k:row[k] for k in KEYS},status=old.get('status','Resultados registrados'))
 data['competitions']=list(existing.values())
 data['fields'].update(season_start=evidence['seasonStart'],results_source='fixtures-and-validated-standings')
 table=evidence.get('club_tables',{}).get(str(data['club']),[])
 row=next((r for r in table if r['club']==data['club']),None)
 if row:data['fields'].update(league_rank=row['rank'],league_points=row['points'],league_games=row['played'])

def project(game,save,club,cache=None,snapshot=None,live=None):
 game=Path(game);cache=cache or ProjectionCache();raw,dbs,base=cache.load(game,save)
 def table(name,fields,base_only=False):
  matches=[db for db in dbs if name in db.tables]
  if len(matches)>1:raise ValueError('Tabela de técnico ambígua: '+name)
  db=matches[0] if matches and not base_only else base
  if name not in db.tables:return []
  key=('coach',id(db),name,tuple(fields))
  if key not in cache.rows:
   def value(index,field):
    try:return db.value(db.tables[name],index,field)
    except UnicodeDecodeError:
     kind,bit,depth,low=db.tables[name]['fields'][field]
     if kind!=0:return None
     at=db.tables[name]['records']+index*db.tables[name]['stride']+bit//8
     return db.data[at:at+depth//8].split(b'\0',1)[0].decode('cp1252',errors='replace')
   cache.rows[key]=[{field:value(i,field) for field in fields} for i in range(db.tables[name]['rows'])]
  return cache.rows[key]
 def match(name,fields,key,ids):
  return [r for r in table(name,fields) if r.get(key) in ids]
 team=match('teams',['teamid','teamname',*('teamcolor'+str(i)+ch for i in (1,2,3) for ch in 'rgb')],'teamid',{club})
 if len(team)!=1:raise ValueError('Clube não disponível nesta carreira.')
 managers=match('manager',['teamid','firstname','surname'],'teamid',{club})
 users=table('career_users',['userid','usertype','clubteamid','firstname','surname','nationalityid'])
 info=table('career_managerinfo',['userid','clubteamid','boardconfidence','managerreputation','wage'])
 manager=manager_for(club,managers,users,info)
 name=' '.join(str(manager.get(k) or '').strip() for k in ('firstname','surname')).strip()
 if name.casefold().startswith(('téc. ','tec. ','coach ','manager ')):name=name.split(' ',1)[1]
 if not name:name=next((r[1].strip() for r in catalog(game/'ModCarrerMode/data/catalogs/club_manager_fallback.tsv') if len(r)>=2 and r[0]==str(club)),'Não informado')
 nation_id=manager.get('nationalityid')
 if nation_id is None:nation_id=next((int(r[2]) for r in catalog(game/'ModCarrerMode/data/catalogs/coach_identity.tsv') if len(r)==3 and r[0]==str(club) and r[1].strip().casefold()==name.casefold() and r[2].isdigit()),None)
 nation=next((r for r in table('nations',['nationid','nationname']) if r['nationid']==nation_id),{})
 league_fields=['leagueid','leaguename','level'];league_rows={r['leagueid']:r for r in table('leagues',league_fields,True)}
 league_rows.update({r['leagueid']:r for r in table('leagues',league_fields)});league_rows=list(league_rows.values());leagues={r['leagueid']:r['leaguename'] for r in league_rows}
 countries={}
 try:
  for line in (game/'ModCarrerMode/data/club_browser/catalog.tsv').read_text(encoding='utf-8-sig').splitlines():
   row=line.split('\t')
   if len(row)==18:countries[int(row[2])]=row[1];leagues[int(row[5])]=row[6]
 except (OSError,ValueError):pass
 # Match preview's already-published native localization cache. Reading it
 # avoids launching a separate localization process while opening this view.
 try:
  loc=game/'data/loc/por_br.db';state=json.loads((game/'ModCarrerMode/runtime/club_environment/preview/runtime/competition_labels_r57.json').read_text(encoding='utf8'))
  if state.get('revision')==3 and state.get('stamp')==[loc.stat().st_mtime_ns,loc.stat().st_size]:
   for ident in {*leagues,*(r[3] for r in (snapshot or {}).get('nodes',[]) if len(r)==5 and r[2]==3 and r[3]>0)}:
    for key in (f'TrophyName_{ident}',f'TrophyName_Abbr15_{ident}',f'LeagueName_{ident}',f'LEAGUE_NAME_{ident}',f'CompetitionName_{ident}',f'TournamentName_{ident}'):
     label=state['names'].get(key)
     if label and '\ufffd' not in label:leagues[ident]=label;break
 except (OSError,ValueError,KeyError,TypeError):pass
 links=match('leagueteamlinks',['teamid','leagueid','secondarytable'],'teamid',{club});members={r['leagueid'] for r in links if not r.get('secondarytable')}
 primary=min((r for r in league_rows if r['leagueid'] in members),key=lambda r:r.get('level') or 99,default={})
 from coach_portrait import portrait
 fields=dict(name=name,portrait=portrait(game,name),country=countries.get(nation_id,nation.get('nationname','—')),nation=nation_id or 0,league=leagues.get(primary.get('leagueid'),'—'),league_id=primary.get('leagueid',0))
 for src,dest,maximum in [('boardconfidence','confidence',100),('managerreputation','reputation',1501),('wage','weekly_wage',2147483647)]:
  v=manager.get(src);fields[dest]=v if type(v)==int and 0<=v<=maximum else -1
 fields['monthly_wage']=round(fields['weekly_wage']*52/12) if fields['weekly_wage']>0 else -1
 sheets=match('teamsheets',['teamid','isfavourite','formationid'],'teamid',{club});sheets=[r for r in sheets if r.get('isfavourite')==1]
 formation_id=sheets[0].get('formationid') if len(sheets)==1 else None
 fields['formation']=next((r['formationname'] for r in table('formations',['formationid','formationname']) if r['formationid']==formation_id),'—')
 if fields['formation']=='—':fields['formation']=next((r[1] for r in catalog(game/'ModCarrerMode/data/catalogs/club_formation_fallback.tsv') if len(r)>1 and r[0]==str(club)),'—')
 stadium_links=match('teamstadiumlinks',['teamid','stadiumid'],'teamid',{club});sid=stadium_links[0].get('stadiumid') if len(stadium_links)==1 else 0
 stadium=next((r for r in table('stadiums',['stadiumid','name','capacity']) if r['stadiumid']==sid),{})
 # Reuse the match-preview resolver, including the club's custom DB name.
 from preview_details import stadium_title
 class Row:
  def __init__(self,row):self.row=row
  def value(self,key):return self.row.get(key)
 assigned=table('stadiumassignments',['teamid','stadiumcustomname'])
 fields['stadium']=stadium_title(club,0,lambda name:[Row(r) for r in assigned] if name=='stadiumassignments' else [],{},stadium.get('name',''),game)[0]
 fields['capacity']=stadium.get('capacity') or -1
 calendar=table('career_calendar',['currdate','startdate']);fields['date']=snapshot['date'] if snapshot else calendar[0].get('currdate',0) if len(calendar)==1 else 0
 fields['season_year']=calendar[0].get('startdate',0)//10000 if len(calendar)==1 else 0
 since=calendar[0].get('startdate',0) if len(calendar)==1 else 0
 stats,competitions,form=season(snapshot,club,leagues,lambda m:m['date']>=since);fields['form']=form or '—';history=[]
 history_fields=['teamid','season','games_played','wins','draws','losses','goals_for','goals_against','points','tableposition','leaguetrophies','domesticcuptrophies','continentalcuptrophies']
 for r in match('career_managerhistory',history_fields,'teamid',{club}):
  values=[r.get(k) for k in ('games_played','wins','draws','losses','goals_for','goals_against','points')]
  if any(type(v)!=int or v<0 for v in values) or sum(values[1:4])!=values[0]:continue
  history.append(dict(season=(r.get('season') or 0)+1,rank=r.get('tableposition') or -1,**dict(zip(KEYS,values)),titles=sum(r.get(k) or 0 for k in ('leaguetrophies','domesticcuptrophies','continentalcuptrophies'))))
 history.sort(key=lambda r:r['season'],reverse=True)
 colors=[sum((team[0].get('teamcolor'+str(i)+ch) or 0)<<shift for ch,shift in zip('rgb',(16,8,0))) for i in (1,2,3)]
 data=dict(club=club,club_name=team[0]['teamname'],fields=fields,stats=stats,coach_stats={},competitions=competitions,history=history,starters=[],save_hash=cache.save_hash,fixture=struct.pack('<8s4I',b'FFCOACH1',club,*colors))
 if snapshot:
  from ranking_data import merge_schedule
  from competition_formats import read_formats
  from competition_schedule import read_schedule
  from career_results import from_career
  formats=read_formats(game);schedule=merge_schedule(read_schedule(raw,formats),snapshot,formats)
  apply_results(data,from_career(game,cache,dbs,base,snapshot,schedule,live),leagues)
 return data

def attach_market(data,market,snapshot,game):
 fields=data['fields'];fields.update(coach_available=0,coach_form='—')
 if not market:return
 person=market['coach'];a=market['appointment'];start=market['start'];today=fields['date'];data['coach_stats'],form=tenure(market,snapshot,data['club'])
 # Aggregate counters have no appointment/date per match. Only an explicitly
 # recorded initial spell can own the entire current campaign.
 if a.get('origin')=='Vínculo inicial desde o início da carreira' and 0<fields.get('season_start',0)>=start:
  from copy import deepcopy
  data['coach_stats']=deepcopy(data['stats']);form=fields.get('form','—')
 elif data['stats'].get('games',0)>0 and data['coach_stats'].get('games')==0:
  # A simulated league may retain team totals without any dated fixtures.
  # Do not turn missing spell ownership into a claim of zero coach matches.
  data['coach_stats']={}
  fields['coach_stats_note']='Sem partidas individualizadas para confirmar esta passagem'
 from coach_portrait import portrait
 fields['portrait']=portrait(game,person['name'],person)
 from datetime import date
 elapsed=(date(today//10000,today//100%100,today%100)-date(start//10000,start//100%100,start%100)).days
 fields.update(name=person['name'],monthly_wage=a['monthly_wage'],coach_available=1,coach_since=f'{start%100:02d}/{start//100%100:02d}/{start//10000}',coach_days=elapsed,coach_form=form or '—')
 human=person.get('coach_id','').startswith('USER-')
 if not human:
  fields['reputation']=round(max(1,min(10,person['reputation']))*1501/10)
  fields['confidence']=market.get('confidence',{}).get('value',-1)
 if human and not person['nationality']:return
 try:
  from manager_market.catalog_meta import Labels
  path=Path(game)/'ModCarrerMode/data/manager_market/catalog.sqlite3'
  if not path.is_file():raise OSError('Catálogo indisponível')
  country,flag=Labels(path).nationality(person['nationality']);fields['country']=country;fields['nation']=int(flag.split('_')[-1]) if flag.split('_')[-1].isdigit() else 0
 except (OSError,ValueError,sqlite3.Error):fields['country']=person['nationality'] or '—';fields['nation']=0

def tsv(data):
 rows=[['S16COACH1',data['club'],data['club_name']]]
 rows.extend(['F',k,v] for k,v in data['fields'].items())
 for key in ('total','home','away'):
  s=data['stats'] if key=='total' else data['stats'].get(key,{})
  rows.append(['S',key,*(s.get(k,-1) for k in KEYS)])
  s=data.get('coach_stats',{}) if key=='total' else data.get('coach_stats',{}).get(key,{})
  rows.append(['T',key,*(s.get(k,-1) for k in KEYS)])
 rows.extend(['C',r['asset'],r['name'],*(r.get(k,-1) for k in KEYS),r['status']] for r in data['competitions'])
 rows.extend(['H',r['season'],r['rank'],*(r[k] for k in KEYS),r['titles']] for r in data['history'])
 rows.extend(['X',r['id'],r['number'],r['name'],r['position'],r['overall']] for r in data['starters'])
 return ('\n'.join('\t'.join(map(clean,row)) for row in rows)+'\n').encode('utf8')
