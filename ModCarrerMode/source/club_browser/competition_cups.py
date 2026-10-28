"""Generic cup structure. Stage identities come from FCE, never a cup whitelist."""
from collections import defaultdict

STAGES={2:'Fase de grupos',3:'Primeira fase',4:'Segunda fase',5:'32 avos de final',6:'Oitavas de final',7:'Quartas de final',8:'Semifinais',9:'Terceiro lugar',10:'Final'}

def build_cup(nodes,root,tables,fixtures,club,today,rules=lambda group:([],{}),formats=None):
 formats=formats or {}
 def phase(identifier):
  seen=set()
  while identifier in nodes and identifier not in seen:
   seen.add(identifier);n=nodes[identifier]
   if n[2]==4:return n[0],formats.get(n[0],{}).get('kind',n[4])
   identifier=n[1]
  return None,0
 groups=[]
 for key,rows in sorted(tables.items()):
  parent,kind=phase(key)
  if kind!=2:continue  # Setup pools and two-team knockout groups are not round robins.
  legend,zones=rules(key)
  for row in rows:
   zone=zones.get(row['rank']);row.update(zone=zone['key'] if zone else '',zoneColor=zone['color'] if zone else None)
  groups.append(dict(id=key,stage=parent,name='Grupo '+chr(65+len(groups)) if len(groups)<26 else 'Grupo '+str(len(groups)+1),rows=rows,legend=legend))
 pairs=defaultdict(list)
 for m in fixtures:
  kind=m.get('stageKind',0)
  if kind<=2:continue
  # A pair can meet in more than one phase: the stage is part of the identity.
  key=(kind,m.get('stage',0),*sorted((m['home'],m['away'])))
  pairs[key].append(m)
 rounds=defaultdict(list)
 for (kind,stage,a,b),legs in pairs.items():
  legs.sort(key=lambda m:(m['date'],m['id']))
  first=legs[0];a,b=first['home'],first['away']
  completed=[m for m in legs if m.get('played') and m['date']<=today and m.get('homeScore') is not None and m.get('awayScore') is not None]
  totalA=sum(m['homeScore'] if m['home']==a else m['awayScore'] for m in completed)
  totalB=sum(m['homeScore'] if m['home']==b else m['awayScore'] for m in completed)
  # Never invent a penalty winner or use an unfinished first leg as qualification.
  expected=2 if formats.get(stage,{}).get('mode')=='KO2LEGS' else 1
  done=len(legs)>=expected and len(completed)==len(legs)
  winner=a if done and totalA>totalB else b if done and totalB>totalA else None
  rounds[(kind,stage)].append(dict(home=a,away=b,homeName=first.get('homeName','Clube'),awayName=first.get('awayName','Clube'),aggregateHome=totalA if completed else None,aggregateAway=totalB if completed else None,complete=done,winner=winner,legs=legs))
 result=[]
 for stage,info in formats.items():
  if info['root']==root and info['mode'].startswith('KO'):rounds.setdefault((info['kind'],stage),[])
 for (kind,stage),ties in sorted(rounds.items(),key=lambda item:item[0][1]):
  ties.sort(key=lambda t:(min(m['id'] for m in t['legs']),t['home']))
  result.append(dict(kind=kind,stage=stage,name=formats.get(stage,{}).get('name',STAGES.get(kind,'Eliminatória')),ties=ties))
 # Put predecessor ties next to the actual successor. Do not guess a draw by rank.
 for i in range(len(result)-2,-1,-1):
  following=result[i+1]
  if following['kind']==9 or result[i]['kind']==9:continue
  order={team:j for j,t in enumerate(following['ties']) for team in (t['home'],t['away'])}
  result[i]['ties'].sort(key=lambda t:min(order.get(t['home'],10**9),order.get(t['away'],10**9)))
 own=[m for m in fixtures if club in (m['home'],m['away'])]
 future=any(not m.get('played') and m['date']>=today for m in own)
 own_done=[m for m in own if m.get('played') and m['date']<=today]
 other_future=any(not m.get('played') and m['date']>=today for m in fixtures)
 eliminated=False
 own_ties=[(r,t) for r in result for t in r['ties'] if club in (t['home'],t['away'])]
 if own_done and not future:
  last=max(own_done,key=lambda m:(m['date'],m['id']))
  last_tie=next((t for r,t in reversed(own_ties) if any(m['id']==last['id'] for m in t['legs'])),None)
  if last_tie and last_tie['complete'] and last_tie['winner'] is not None:
   eliminated=last_tie['winner']!=club
  elif other_future:
   candidates=[g for g in groups if any(p['team']==club for p in g['rows'])]
   for g in candidates:
    row=next(p for p in g['rows'] if p['team']==club)
    full=all(p['games']>0 for p in g['rows'])
    later=any(m.get('stageKind',0)>2 and m['date']>last['date'] for m in fixtures)
    if full and later and g['legend'] and not row.get('zone'):eliminated=True
 finals=[t for r in result if r['kind']==10 for t in r['ties'] if club in (t['home'],t['away'])]
 if finals and finals[-1]['winner'] is not None:eliminated=finals[-1]['winner']!=club
 awaiting=not future and bool(own_ties) and own_ties[-1][1]['winner']==club and own_ties[-1][0]['kind']!=10
 return dict(groups=groups,rounds=result,eliminated=eliminated,awaitingDraw=awaiting)
