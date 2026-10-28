"""On-demand competition export. Query/read-only process, immutable native save."""
from pathlib import Path
import json,time
from competitions_data import project
from season_stats import current
from server16_py.career_context import competition_session

def tsv(data,seq):
 rows=[['H',1,seq,data['club'],data['date'],data['clubName']]]
 for c in data['competitions']:
  root=c['root'];rows.append(['C',root,c['asset'],c['name'],c['format'],c['statusLabel'],c.get('clubRank'),c.get('clubPoints')])
  groups=[dict(id=0,name='Classificação',rows=c['table'],legend=c.get('legend',[]))] if c['format']=='league' else c.get('groups',[])
  for group in groups:
   gid=group['id'];rows.append(['G',root,gid,group['name']])
   for p in group['rows']:
    rows.append(['T',root,gid,p['team'],p['rank'],p['name'],p['games'],p['wins'],p['draws'],p['losses'],p['goalsFor'],p['goalsAgainst'],p['points'],p.get('movement',0),''.join(p.get('form',[])),p.get('zoneColor')])
   for z in group.get('legend',[]):rows.append(['Z',root,gid,z['color'],z['label']])
  for i,r in enumerate(c.get('rounds',[])):
   rows.append(['R',root,i,r['stage'],r['kind'],r['name']])
   for j,t in enumerate(r['ties']):
    rows.append(['K',root,i,j,t['home'],t['away'],t['homeName'],t['awayName'],t['aggregateHome'],t['aggregateAway'],t['winner'],int(t['complete'])])
    for leg in t['legs']:
     rows.append(['L',root,i,j,leg['date'],leg['time'],leg['home'],leg['away'],leg['homeScore'] if leg['played'] else None,leg['awayScore'] if leg['played'] else None])
  for kind in ('goals','assists'):
   for p in c.get(kind,[]):rows.append(['S',root,kind,p['id'],p['club'],p['name'],p['clubName'],p['value'],p['appearances'],p.get('position','')])
  for n in c.get('bracket',{}).get('nodes',[]):rows.append(['N',root,n['id'],n['round'],n['tie'],round(n['x']),round(n['y'])])
  for e in c.get('bracket',{}).get('edges',[]):rows.append(['E',root,e['source'],e['destination'],e['rank'],e['slot']])
  team=c.get('teamOfCompetition',{});rows.append(['F',root,team.get('formation',''),team.get('ratedPlayers',0)])
  for p in team.get('starters',[]):rows.append(['X',root,p['slot'],p['id'],p['club'],p['name'],f"{p['averageRating']:.1f}"])
 def field(value):return str(value if value is not None else '').replace('\t',' ').replace('\r',' ').replace('\n',' ')
 return ('\n'.join('\t'.join(map(field,r)) for r in rows)+'\n').encode('utf8')

def generate(game,folder,req,memory,projection_cache):
 from lineup_worker import observe,request,atomic,publish
 began=time.monotonic();saved,context=observe(memory,game);snapshot=None
 while time.monotonic()-began<12:
  if request(folder/'request.tsv',req['pid'])!=req:return False
  profile=competition_session(memory,True);snapshot=current(game,memory,saved,profile)
  if snapshot:break
  after,ctx=observe(memory,game)
  if ctx!=context or (after['path'],after['mtime_ns'])!=(saved['path'],saved['mtime_ns']):
   publish(folder,req,'error',kind='competitions',retry=1,message='Atualizando a carreira selecionada.');return True
  time.sleep(.1)
 if not snapshot:
  publish(folder,req,'error',kind='competitions',retry=1,message='Aguardando a publicação atual dos dados da carreira.');return True
 if snapshot['club']!=req['club']:raise ValueError('O clube da carreira mudou. Abra Competições novamente.')
 data=project(game,Path(saved['path']),snapshot,projection_cache)
 after,ctx=observe(memory,game)
 latest=current(game,memory,after,competition_session(memory,True))
 if request(folder/'request.tsv',req['pid'])!=req:return False
 if ctx!=context or latest is None or latest['date']!=snapshot['date'] or latest.get('generation')!=snapshot.get('generation') or (after['path'],after['mtime_ns'])!=(saved['path'],saved['mtime_ns']):
  publish(folder,req,'error',kind='competitions',retry=1,message='A carreira mudou durante a leitura.');return True
 atomic(folder/'competitions.tsv',tsv(data,req['seq']))
 publish(folder,req,'ready',kind='competitions',date=data['date'],competitions=len(data['competitions']))
 return True
