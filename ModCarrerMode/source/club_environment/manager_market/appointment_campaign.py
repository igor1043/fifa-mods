"""Aggregate campaign evidence attributed to a contract, without fake fixtures."""
import json
from collections import defaultdict

KEYS=('hw','hd','hl','aw','ad','al')
INITIAL=('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod')

def retain_closed(market,context=None,appointment=None):
 """Recover only evidence already observed on/before a closed initial spell.

 A late current total cannot be backdated. Equality with the handover vector
 is required before enriching the preserved counts with current goal totals.
 """
 appointments=[appointment] if appointment is not None else market.rows('appointments','end_date IS NOT NULL')
 appointments=[a for a in appointments if a['origin'] in INITIAL]
 if not appointments:return
 club=appointment['club_id'] if appointment is not None else None
 previous=defaultdict(list)
 for r in market.rows('performance_evidence','club_id=?' if club is not None else '',(club,) if club is not None else ()):previous[r['club_id']].append(r)
 campaigns=market.rows('appointment_campaigns','appointment=?' if appointment is not None else '',(appointment['id'],) if appointment is not None else ());stored={(r['appointment'],r['season'],r['competition_key']) for r in campaigns}
 assets={(r['season'],r['competition_key']):r['asset'] for r in reversed(campaigns)}
 current={(r['season'],r['key'],r['club']):r for r in (context or {}).get('performance',[])}
 for a in appointments:
  for r in previous[a['club_id']]:
   if r['game_date']>a['end_date'] or r['game_date']<a['start_date']:continue
   key=(a['id'],r['season'],r['competition_key'])
   if key in stored:continue
   parts=r['competition_key'].split(':');root=int(parts[1]) if parts[0]=='fce' else 0
   candidate=current.get((r['season'],r['competition_key'],r['club_id']))
   if candidate:asset=candidate['asset']
   elif parts[0]=='db':asset=int(parts[1])
   else:
    asset=assets.get((r['season'],r['competition_key']))
    if asset is None and appointment is not None:
     known=market.db.execute('SELECT asset FROM appointment_campaigns WHERE branch=? AND season=? AND competition_key=? LIMIT 1',(market.branch,r['season'],r['competition_key'])).fetchone()
     if known:asset=known[0]
    if asset is None:continue
   values=[r[k] for k in KEYS]
   if candidate and values==[candidate[k] for k in KEYS] and all(k in candidate for k in ('hgf','hga','agf','aga')):values.extend(candidate[k] for k in ('hgf','hga','agf','aga'))
   market.db.execute('INSERT OR IGNORE INTO appointment_campaigns VALUES(?,?,?,?,?,?,?,?,?,?)',(market.branch,a['id'],r['season'],r['competition_key'],root,asset,r['game_date'],json.dumps([0]*len(values)),json.dumps(values),'handover_evidence'))
   stored.add(key)
   assets.setdefault((r['season'],r['competition_key']),asset)

def capture(market,context):
 retain_closed(market,context)
 active={a['club_id']:a for a in market.rows('appointments','end_date IS NULL')}
 previous={(r['season'],r['competition_key'],r['club_id']):r for r in market.rows('performance_evidence')}
 stored={(r['appointment'],r['season'],r['competition_key']):r for r in market.rows('appointment_campaigns')}
 by_history=defaultdict(list);by_asset=defaultdict(list)
 for r in stored.values():
  by_history[(r['appointment'],r['competition_key'])].append(r)
  by_asset[(r['appointment'],r['season'],r['asset'])].append(r)
 from annual_campaigns import seed as seed_years
 seed_years(market,stored.values())
 annual={(r['appointment'],r['year'],r['competition_key']):r for r in market.rows('annual_campaigns')}
 for r in context.get('performance',[]):
  a=active.get(r['club'])
  if not a or r['date']>context['date']:continue
  # A temporary league-only poll must not replace the richer campaign and
  # its original appointment baseline. Full native evidence will catch up
  # without resetting the coach's already observed games/goals.
  if context.get('coverage',{}).get('league_only') and not r['root'] and any(v['root'] for v in by_asset[(a['id'],r['season'],r['asset'])]):continue
  key=(a['id'],r['season'],r['key']);old=stored.get(key)
  prior=old or max((v for v in by_history[(a['id'],r['key'])] if v['game_date']<=r['date']),key=lambda v:v['game_date'],default=None)
  for other in by_asset[(a['id'],r['season'],r['asset'])]:
   if bool(other['root'])!=bool(r['root']) and '#cycle:' not in other['competition_key']:
    market.db.execute('DELETE FROM appointment_campaigns WHERE branch=? AND appointment=? AND season=? AND competition_key=?',(market.branch,a['id'],r['season'],other['competition_key']))
  if old and old['game_date']>r['date']:continue
  values=[r[k] for k in KEYS]
  if all(k in r for k in ('hgf','hga','agf','aga')):values.extend(r[k] for k in ('hgf','hga','agf','aga'))
  year_row=annual.get((a['id'],r['date']//10000,r['key']));encoded=json.dumps(values)
  if old and year_row and all(row['game_date']==r['date'] and row['root']==r['root'] and row['asset']==r['asset'] and row['source']==r['source'] and row['counters']==encoded for row in (old,year_row)):
   continue
  if old:
   base=json.loads(old['baseline']);last=json.loads(old['counters'])
   if len(values)>len(base):base.extend(values[len(base):])
   if r['date']>old['game_date'] and sum(values[:6])<sum(last[:6]):
    archived={k:v for k,v in old.items() if k!='branch'};archived['competition_key']=r['key']+'#cycle:'+str(r['date'])
    market.add('appointment_campaigns',archived);base=[0]*len(values)
  elif prior and prior['season']!=r['season']:
   last=json.loads(prior['counters']);base=last[:] if sum(values[:6])>=sum(last[:6]) else [0]*len(values)
   if len(values)>len(base):base.extend(values[len(base):])
  elif a['origin'] in INITIAL:base=[0]*len(values)
  else:
   evidence=previous.get((r['season'],r['key'],r['club']))
   # A snapshot predating the appointment is a valid baseline. A later
   # snapshot cannot tell us which games belonged to the predecessor.
   base=[evidence[k] for k in KEYS] if evidence and evidence['game_date']==a['start_date'] else values[:]
   if len(values)>len(base):base.extend(values[len(base):])
  from annual_campaigns import observe as observe_year
  observe_year(market,a,r,prior,base)
  market.db.execute('INSERT OR REPLACE INTO appointment_campaigns VALUES(?,?,?,?,?,?,?,?,?,?)',
   (market.branch,a['id'],r['season'],r['key'],r['root'],r['asset'],r['date'],json.dumps(base),json.dumps(values),r['source']))

def overlay(spells,appointments,results,campaigns):
 """Merge by competition and outcome; aggregate and detailed games overlap."""
 for spell in spells:
  ids=set(spell.pop('_appointments',()))
  rows=[r for r in campaigns if r['appointment'] in ids]
  if not rows:continue
  native_assets={(r['season'],r['asset']) for r in rows if r['root']}
  rows=[r for r in rows if r['root'] or (r['season'],r['asset']) not in native_assets]
  buckets={};goal_buckets={}
  for r in rows:
   key=(r['season'],r['root'],r['asset']);b=buckets.setdefault(key,[0]*6)
   for i,(v,start) in enumerate(zip(json.loads(r['counters'])[:6],json.loads(r['baseline'])[:6])):b[i]+=max(0,v-start)
   counters=json.loads(r['counters']);baseline=json.loads(r['baseline'])
   if len(counters)==10 and len(baseline)==10:
    goals=goal_buckets.setdefault(key,[0]*4)
    for i in range(4):goals[i]+=max(0,counters[i+6]-baseline[i+6])
  deltas=[0]*6;goal_deltas=[0]*4
  for (season,root,asset),counts in buckets.items():
   actual=[0]*6;actual_goals=[0]*4
   for r in results:
    if r.get('season')!=season or (r.get('root')!=root if root else r.get('competition_id')!=asset):continue
    for side,offset,gf,ga in (('home',0,r['hg'],r['ag']),('away',3,r['ag'],r['hg'])):
     if r.get(side+'_appointment') in ids:
      actual[offset+(0 if gf>ga else 1 if gf==ga else 2)]+=1
      g=0 if side=='home' else 2;actual_goals[g]+=gf;actual_goals[g+1]+=ga
   # FIFA may record a penalty winner as W/L while the retained score is a
   # draw. Replace the outcome vector for this same campaign; componentwise
   # maxima would count that one game twice.
   if sum(counts)>=sum(actual):
    for i in range(6):deltas[i]+=counts[i]-actual[i]
   for i,v in enumerate(goal_buckets.get((season,root,asset),[])):goal_deltas[i]+=max(0,v-actual_goals[i])
  for name,offset in (('home',0),('away',3)):
   out=spell[name]
   for i,k in enumerate(('wins','draws','losses')):out[k]+=deltas[offset+i]
   g=0 if name=='home' else 2;out['gf']+=goal_deltas[g];out['ga']+=goal_deltas[g+1]
   recalc(out)
  for k in ('games','wins','draws','losses','gf','ga','points'):spell['total'][k]=spell['home'][k]+spell['away'][k]
  recalc(spell['total'])

def recalc(out):
 out['games']=out['wins']+out['draws']+out['losses'];out['points']=3*out['wins']+out['draws']
 out['percentage']=round(100*out['points']/(3*out['games']),1) if out['games'] else 0
