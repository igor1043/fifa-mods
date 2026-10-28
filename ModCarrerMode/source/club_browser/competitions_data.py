"""Competition views from the validated current career publication and read-only save."""
from pathlib import Path
from lineup_data import ProjectionCache
from competition_schedule import read_schedule,read_assignment_roots,_apply_league_table_movements
from competition_team import build_competition_statistics
from competition_rules import read_rules
from competition_cups import build_cup
from competition_formats import read_formats
from competition_bracket import build as build_bracket
import csv
import json

def project(game,save,snapshot,cache=None):
 GAME=Path(game);save=Path(save);cache=cache or ProjectionCache()
 raw,dbs,base=cache.load(GAME,save);club=snapshot['club'];today=snapshot['date']
 def rows(name,fields,base_only=False):
  matches=[db for db in dbs if name in db.tables];db=matches[0] if len(matches)==1 and not base_only else base
  if name not in db.tables:return []
  def value(i,f):
   try:return db.value(db.tables[name],i,f)
   except UnicodeDecodeError:
    k,bit,depth,low=db.tables[name]['fields'][f];at=db.tables[name]['records']+i*db.tables[name]['stride']+bit//8
    return db.data[at:at+depth//8].split(b'\0',1)[0].decode('cp1252',errors='replace') if k==0 else None
  return [{f:value(i,f) for f in fields} for i in range(db.tables[name]['rows'])]
 teams={r['teamid']:r['teamname'] for r in rows('teams',['teamid','teamname'])};league_names={r['leagueid']:r['leaguename'] for r in rows('leagues',['leagueid','leaguename'],True)}
 league_ids={r['leagueid'] for r in rows('leagueteamlinks',['teamid','leagueid'])}
 for line in (GAME/'ModCarrerMode/data/club_browser/catalog.tsv').read_text(encoding='utf8').splitlines():
  r=line.split('\t')
  if len(r)==18:league_names[int(r[5])]=r[6]
 labels_path=GAME/'ModCarrerMode/runtime/club_environment/preview/runtime/competition_labels_r57.json'
 if labels_path.is_file():
  labels=json.loads(labels_path.read_text(encoding='utf8')).get('names',{})
  for key,value in labels.items():
   for prefix in ('TrophyName_','TrophyName_Abbr15_','LeagueName_'):
    if key.startswith(prefix) and key[len(prefix):].isdigit() and value and '\ufffd' not in value:league_names[int(key[len(prefix):])]=value
 formats=read_formats(GAME);schedule=read_schedule(raw,formats);assignments=read_assignment_roots(raw).get(club,[])
 advancement=[tuple(map(int,r[:4])) for r in csv.reader((GAME/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/advancement.txt').read_text(encoding='utf-8-sig').splitlines()) if len(r)>=4 and all(v.lstrip('-').isdigit() for v in r[:4])]
 nodes={r[0]:r for r in snapshot['nodes']};roots={r['root']:r['asset'] for r in assignments}
 def root(n):
  seen=set()
  while n in nodes and n not in seen:
   seen.add(n);r=nodes[n]
   if r[2]==3:return r[0],r[3]
   n=r[1]
  return None
 for f in snapshot['fixtures']:
  if club in f[5:7]:
   ident=root(f[1])
   if ident:roots[ident[0]]=ident[1]
 # New draws may exist in RAM before the next manual save. Resolve their
 # stage from a unique live standings group; never guess from a cup's name.
 live_groups={}
 for row in snapshot['standings']:
  if len(row)==10 and row[2]>0:live_groups.setdefault(row[1],set()).add(row[2])
 stored={m['id']:m for m in schedule}
 for f in snapshot['fixtures']:
  ident=root(f[1])
  if len(f)<10 or not ident or ident[0] not in roots:continue
  old=stored.get(f[0])
  if old and (old['home'],old['away'],old['root'])==(f[5],f[6],ident[0]):continue
  candidates=[]
  for gid,members in live_groups.items():
   node=nodes.get(gid);phase=node[1] if node and node[2]==5 else 0;fmt=formats.get(phase,{})
   if f[5] in members and f[6] in members and (root(gid) or (-1,))[0]==ident[0] and fmt.get('mode') in ('LEAGUE','KO1LEG','KO2LEGS'):
    if f[2] in (ident[0],phase,gid):candidates.append((gid,phase,fmt['kind']))
  gid,stage,kind=candidates[0] if len(candidates)==1 else (None,f[2],formats.get(f[2],{}).get('kind',0))
  match=dict(id=f[0],root=ident[0],asset=ident[1],stage=stage,group=gid,stageKind=kind,date=f[3],time=f'{f[4]//100:02d}:{f[4]%100:02d}',home=f[5],away=f[6],homeScore=f[7] if f[9] else None,awayScore=f[8] if f[9] else None,played=bool(f[9]),round=f[10] if len(f)>10 else 0)
  if old:schedule.remove(old)
  schedule.append(match)
 native={f[0]:f for f in snapshot['fixtures']}
 for match in schedule:
  f=native.get(match['id'])
  if f and (match['home'],match['away'],match['root'])==(f[5],f[6],(root(f[1]) or (-1,))[0]):
   match.update(date=f[3],homeScore=f[7] if f[9] else None,awayScore=f[8] if f[9] else None,played=bool(f[9]),time=f'{f[4]//100:02d}:{f[4]%100:02d}',round=f[10] if len(f)>10 else 0)
 player_ids={r[3] for r in snapshot['stats'] if len(r)>=8 and (root(r[1]) or (-1,))[0] in roots}
 fields=['playerid','commonnameid','firstnameid','lastnameid','preferredposition1','preferredposition2','preferredposition3','preferredposition4','overallrating']
 players={r['playerid']:r for r in cache.matching(base,'players',fields,'playerid',player_ids)}
 for db in dbs:
  if 'players' in db.tables:
   for r in cache.matching(db,'players',fields,'playerid',player_ids):players.setdefault(r['playerid'],{}).update({k:v for k,v in r.items() if v is not None})
 wanted={p.get(k) for p in players.values() for k in ('commonnameid','firstnameid','lastnameid')};wanted.discard(None)
 names={r['nameid']:r['name'] for r in cache.matching(base,'playernames',['nameid','name'],'nameid',wanted)}
 names.update({r['nameid']:r['name'] for r in rows('dcplayernames',['nameid','name']) if r['nameid'] in wanted})
 def display(p):return names.get(p.get('commonnameid')) or ' '.join(filter(None,[names.get(p.get('firstnameid')),names.get(p.get('lastnameid'))])) or 'Jogador'
 stats=build_competition_statistics(snapshot,roots,players,display,teams)
 group_members={}
 for row in snapshot['standings']:
  if len(row)==10 and row[2]>0:group_members.setdefault(row[1],set()).add(row[2])
 def form_for(team,fixtures):
  out=[]
  for m in sorted(fixtures,key=lambda m:(m['date'],m['id'])):
   if not m['played'] or m['date']>today or team not in (m['home'],m['away']):continue
   gf,ga=(m['homeScore'],m['awayScore']) if team==m['home'] else (m['awayScore'],m['homeScore'])
   if gf is not None and ga is not None:out.append('V' if gf>ga else 'E' if gf==ga else 'D')
  return out[-5:]
 def standing(row,fixtures):
  # Published standings contain home/away W-D-L counters, not goals/points.
  team=row[2];games=row[9];wins=row[3]+row[6];draws=row[4]+row[7];losses=row[5]+row[8]
  members=group_members.get(row[1],set())
  completed=[m for m in fixtures if m.get('group')==row[1] and m['played'] and m['date']<=today and team in (m['home'],m['away']) and m['homeScore'] is not None and m['awayScore'] is not None and m['home'] in members and m['away'] in members]
  gf=sum(m['homeScore'] if m['home']==team else m['awayScore'] for m in completed);ga=sum(m['awayScore'] if m['home']==team else m['homeScore'] for m in completed)
  return dict(team=team,name=teams.get(team,'Clube'),games=games,wins=wins,draws=draws,losses=losses,goalsFor=gf if len(completed)==games else None,goalsAgainst=ga if len(completed)==games else None,points=wins*3+draws,form=form_for(team,[m for m in fixtures if m.get('group')==row[1]]))
 competitions=[]
 for ident,asset in roots.items():
  fixtures=[m for m in schedule if m['root']==ident];own=[m for m in fixtures if club in (m['home'],m['away'])];is_league=asset in league_ids
  groups={}
  for row in snapshot['standings']:
   if len(row)==10 and (root(row[1]) or (-1,))[0]==ident and row[2]>0:groups.setdefault(row[1],[]).append(standing(row,fixtures))
  for group in groups.values():
   group.sort(key=lambda r:(-r['points'],-r['wins'],-((r['goalsFor'] or 0)-(r['goalsAgainst'] or 0)),-(r['goalsFor'] or 0),r['name']))
   for rank,r in enumerate(group,1):r['rank']=rank
  own_groups=[(key,group) for key,group in groups.items() if any(r['team']==club for r in group)]
  group_id,table=max(own_groups,key=lambda item:len(item[1]),default=(None,[]))
  if table and all(r['goalsFor'] is not None for r in table):_apply_league_table_movements(table,fixtures,today)
  else:
   for row in table:row['movement']=0
  legend,zones=read_rules(GAME,asset,group_id,league_names) if group_id else ([],{})
  for row in table:
   zone=zones.get(row['rank']);row['zone']=zone['key'] if zone else '';row['zoneColor']=zone['color'] if zone else None;row['zoneLabel']=zone['label'] if zone else ''
  future=[m for m in own if not m['played'] and m['date']>=today];played=[m for m in own if m['played'] and m['date']<=today]
  all_future=any(not m['played'] and m['date']>=today for m in fixtures)
  status,label=('active','Em disputa') if future else ('eliminated','Eliminado') if played and all_future and not is_league else ('completed','Concluída') if played and not all_future else ('scheduled','Aguardando sorteio')
  stage=max(played,key=lambda m:(m['date'],m['id'])) if played else min(future,key=lambda m:(m['date'],m['id'])) if future else None
  club_row=next((r for r in table if r['team']==club),None)
  serialized=[dict(**m,homeName=teams.get(m['home'],'Mandante'),awayName=teams.get(m['away'],'Visitante')) for m in fixtures]
  entry=dict(root=ident,asset=asset,name=league_names.get(asset,'Competição da carreira'),format='league' if is_league else 'cup',status=status,statusLabel=label,table=table if is_league else [],groups=[dict(id=key,name='Grupo '+chr(65+i),rows=g) for i,(key,g) in enumerate(own_groups)] if not is_league else [],fixtures=serialized,ownFixtures=[m for m in serialized if club in (m['home'],m['away'])],clubRank=club_row['rank'] if club_row and is_league else None,clubPoints=club_row['points'] if club_row else None,stageKind=stage['stageKind'] if stage else 0)
  entry.update(stats.get(ident,{}));entry['legend']=legend;entry['rulesSource']='CompData instalado · faixas do grupo selecionado'
  if not is_league:
   entry.update(build_cup(nodes,ident,groups,serialized,club,today,lambda key:read_rules(GAME,asset,key,league_names),formats))
   entry['bracket']=build_bracket(entry['rounds'],formats,advancement)
   if entry.get('eliminated'):entry['status']='eliminated';entry['statusLabel']='Eliminado'
   elif entry.get('awaitingDraw'):entry['status']='active';entry['statusLabel']='Aguardando próxima fase'
   elif entry['status']=='eliminated':entry['status']='scheduled';entry['statusLabel']='Aguardando definição'
  competitions.append(entry)
 competitions.sort(key=lambda c:({'active':0,'scheduled':1,'completed':2,'eliminated':3}.get(c['status'],2),c['format']!='league',c['asset']))
 return dict(schema=1,club=club,clubName=teams.get(club,"Clube"),date=today,competitions=competitions)
