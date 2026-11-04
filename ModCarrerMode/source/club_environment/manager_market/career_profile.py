"""Structured career history from appointment IDs, actual scores and honours."""
try:
 from .engine import score,elapsed
 from .board_confidence import for_spell
except ImportError:
 from engine import score,elapsed
 from board_confidence import for_spell

def build(person,appointments,results,honours,reviews,clubs,today,stamp,campaigns=()):
 ident=person['coach_id'];visits=sorted([dict(a,ids=[a['id']]) for a in appointments if a['coach_id']==ident],key=lambda a:(a['start_date'],a['id']))
 # Only explicit renewal movements are merged by the caller via renewal_ids.
 merged=[]
 for a in visits:
  previous=next((v for v in reversed(merged) if v['club_id']==a['club_id'] and v['end_date']==a['start_date'] and v['end_reason']=='renewed'),None)
  if previous and a.get('renewal'):
   previous.update(end_date=a['end_date'],end_reason=a['end_reason'],monthly_wage=a['monthly_wage'],contract_end=a.get('contract_end',previous.get('contract_end',today)));previous['ids']+=a['ids']
  else:merged.append(a)
 all_home=[];all_away=[];spells=[];titles=[];events=[]
 for a in merged:
  ids=set(a['ids']);home=[];away=[]
  for r in results:
   if r.get('home_appointment') in ids:home.append((r['hg'],r['ag']));events.append((r['game_date'],r['match_key'],True,r['hg'],r['ag']))
   if r.get('away_appointment') in ids:away.append((r['ag'],r['hg']));events.append((r['game_date'],r['match_key'],False,r['ag'],r['hg']))
  # Legacy results have coach IDs but no contract ID: use a date only inside
  # an unambiguous spell, never the predecessor's total club results.
  for r in results:
   for side,out in (('home',home),('away',away)):
    if r.get(side+'_appointment') or r.get(side+'_coach')!=ident or r[side]!=a['club_id']:continue
    end=a['end_date'] or today+1
    initial=a['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod')
    if a['start_date']<=r['game_date']<end and (initial or r['game_date']>a['start_date']):
     pair=(r['hg'],r['ag']) if side=='home' else (r['ag'],r['hg']);out.append(pair);events.append((r['game_date'],r['match_key'],side=='home',*pair))
  all_home+=home;all_away+=away;total=score(home+away);hs=score(home);aws=score(away);club=clubs.get(a['club_id'],{})
  own_titles=[h for h in honours if h['coach_id']==ident and h['club_id']==a['club_id'] and a['start_date']<=h['game_date']<(a['end_date'] or today+1)]
  span=stamp(a['start_date'])+' → '+stamp(a['end_date']);days=max(0,elapsed(a['start_date'],a['end_date'] or today))
  spells.append(dict(_appointments=list(ids),contractEnd=a.get('contract_end',a['end_date'] or today),start=a['start_date'],since=stamp(a['start_date']),club=club.get('name','Clube'),clubId=a['club_id'],crest='crest_'+str(a['club_id']),dates=span,duration=str(days)+' dias no cargo',current=a['end_date'] is None,total=total,home=hs,away=aws,titles=len(own_titles),confidence=for_spell(reviews.get(a['club_id'],[]),a['start_date'],a['end_date'] or today,a['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod'))))
 for h in honours:
  if h['coach_id']==ident:titles.append(dict(name=h['name'],competition=h['competition_id'],competitionArt='competition_'+str(h['competition_id']),club=clubs.get(h['club_id'],{}).get('name','Clube'),crest='crest_'+str(h['club_id']),year=str(h['season']//10000),date=stamp(h['game_date'])))
 try:from .appointment_campaign import overlay,recalc
 except ImportError:from appointment_campaign import overlay,recalc
 overlay(spells,appointments,results,campaigns)
 for spell,a in zip(spells,merged):
  spell['confidence']=for_spell(reviews.get(a['club_id'],[]),a['start_date'],a['end_date'] or today,a['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod'),spell['total'])
 totals={}
 for name in ('total','home','away'):
  out={k:sum(v[name][k] for v in spells) for k in ('games','wins','draws','losses','gf','ga','points')};recalc(out);totals[name]=out
 events.sort(key=lambda r:(r[0],r[1]));recent={}
 for name,venue in (('all',None),('home',True),('away',False)):
  own=[r for r in events if venue is None or r[2]==venue][-10:];recent[name]=''.join('V' if gf>ga else 'E' if gf==ga else 'D' for _,_,_,gf,ga in own)
 return dict(**totals,spells=sorted(spells,key=lambda a:a['start'],reverse=True),titles=sorted(titles,key=lambda h:h['year'],reverse=True),clubs=len({a['club_id'] for a in merged}),recent=recent)
