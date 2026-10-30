"""Deterministic extra club finances. The bank bridge alone publishes money.

The book is embedded in the existing per-club/native-save loan state. TV is
one entitlement per completed fixture; monthly totals never generate credits.
"""
from copy import deepcopy
from datetime import date,timedelta
from calendar import monthrange
import math
from loans import MAX_BUDGET,parse_date

LEGACY_RULES={'tv_match_bps':75,'tv_min':10000,'tv_max':1500000,
 'ticket_price':25,'occupancy_min_bps':4500,'occupancy_max_bps':9500}
DEFAULT_RULES={**LEGACY_RULES,'tv_match_bps':150,'ticket_price':8,
 'occupancy_min_bps':3500,'occupancy_max_bps':8500,'match_cost_bps':4000,
 'sponsor_annual_bps':2500,'staff_annual_bps':3000}
# Preserve the first five wire indexes used by existing loan/finance requests.
SWITCHES=('enabled','tv','tickets','coach','loans','sponsor','staff','match_costs')
MONTHLY_KINDS=('coach','sponsor','staff')

def packed(day):return day.year*10000+day.month*100+day.day

def median_value(values):
 values=sorted(values);return (values[(len(values)-1)//2]+values[len(values)//2])//2

def rules(values=None):
 out=dict(DEFAULT_RULES);out.update(values or {})
 for key,v in out.items():
  if key not in DEFAULT_RULES or type(v) is not int or not 0<=v<=10_000_000:raise ValueError('Parâmetro financeiro inválido: '+key)
 if (out['tv_min']>out['tv_max'] or not 0<=out['occupancy_min_bps']<=out['occupancy_max_bps']<=10000
     or out['match_cost_bps']>10000 or out['sponsor_annual_bps']>20000 or out['staff_annual_bps']>20000):raise ValueError('Faixas financeiras inválidas')
 return out

def fixture_key(season,match):
 return f"{season}:{match['root']}:{match['id']}:{match['home']}:{match['away']}"

def settings_at(book,day):
 result=dict.fromkeys(SWITCHES,True)
 for row in book['settings_history']:
  if row['date']<=day:result.update(row['values'])
 return result

def active(book,kind,day):
 s=settings_at(book,day);return s['enabled'] and s[kind]

def toggle(state,kind,value,today):
 if kind not in SWITCHES or type(value) is not bool:raise ValueError('Opção financeira inválida')
 result=deepcopy(state);book=result['finance'];parse_date(today)
 if today<book['last_date']:raise ValueError('Data financeira retrocedeu')
 book['settings_history'].append(dict(date=today,values={kind:value}))
 book['settings'][kind]=value
 result['last_date']=today
 return result

def league_factor(profile):
 """Financial strength proxy from installed league peers, not a nation list."""
 if not profile or not profile.get('league_budget'):return 1.0
 budget=max(100_000,int(profile['league_budget']))
 overall=max(30,min(99,int(profile.get('league_overall') or 60)))
 prestige=max(0,min(20,int(profile.get('league_prestige') or 0)))
 level=max(1,min(8,int(profile.get('level') or 1)))
 return max(.25,min(2.2,math.sqrt(budget/10_000_000)*(0.55+overall*.0045)*(.7+prestige*.03)/math.sqrt(level)))

def agreement(profile,season,today,policy,club_profile=None):
 budgets=[v for v in profile.get('budgets',[]) if type(v) is int and v>0]
 base=median_value(budgets) if budgets else 1_000_000
 prestige=max(1,min(20,int(profile.get('prestige') or 5)))
 level=max(1,min(8,int(profile.get('level') or 1)))
 per_match=base*policy['tv_match_bps']*(50+prestige*5)//(10000*100*level)
 club_prestige=max(1,min(20,int((club_profile or {}).get('prestige') or prestige)))
 factor=league_factor(club_profile)
 per_match=int(per_match*factor*(.65+.035*club_prestige))
 per_match=max(policy['tv_min'],min(policy['tv_max'],per_match))
 return dict(id=f"{season}:{profile['root']}",root=profile['root'],asset=profile['asset'],
  name=profile['name'],season=season,start=today,per_match=per_match,club_profile=deepcopy(club_profile or {}),
  base_budget=base,prestige=prestige,club_prestige=club_prestige,league_factor=round(factor,4),level=level,rules=deepcopy(policy),
  source='Simulação do mod · dados da competição e dos clubes')

def economy_signature(context):
 return list((context.get('club_profile') or {}).get(k) for k in ('league','level','league_budget','league_prestige','league_overall','prestige','base_budget'))

def initial(club,today,context,policy):
 return dict(schema=2,economy_version=3,economy_profile=economy_signature(context),club=club,start=today,last_date=today,season=context['season'],expanded_start=today,
  settings=dict.fromkeys(SWITCHES,True),settings_history=[dict(date=today,values=dict.fromkeys(SWITCHES,True))],
  baseline=[fixture_key(context['season'],m) for m in context['fixtures'] if m['played']],
  agreements={},entries=[],payroll=[dict(date=today,wage=context['coach_wage'])],rules=policy)

def commercial(context,policy):
 """One sponsor and one staff allocation per club/season, never per competition."""
 profile=context.get('club_profile',{})
 budget=max(0,int(profile.get('base_budget') or 0))
 if not budget:
  reference=[v for c in context['competitions'] for v in c.get('budgets',[]) if type(v) is int and v>0]
  budget=median_value(reference) if reference else 1_000_000
 prestige=max(1,min(20,int(profile.get('prestige') or 5)))
 strength=40+prestige*3
 factor=league_factor(profile)
 annual=lambda key:int(budget*policy[key]*strength/1_000_000*(factor if key=='sponsor_annual_bps' else math.sqrt(factor)))
 return dict(base_budget=budget,prestige=prestige,league_factor=round(factor,4),sponsor_annual=annual('sponsor_annual_bps'),
  staff_annual=annual('staff_annual_bps'),source='Estimativa do mod · orçamento-base e reputação do clube')

def ticket_projection(capacity,prestige,policy=None,club_profile=None,*,occupancy_percent=None):
 """Preview the same paying crowd and gross gate used by matchday posting."""
 p=rules(policy);capacity=max(0,int(capacity or 0));prestige=max(1,min(20,int(prestige or 5)))
 if club_profile and club_profile.get('league_budget'):
  p['ticket_price']=max(4,min(40,round(p['ticket_price']*league_factor(club_profile)*(.65+.035*prestige))))
 if capacity<=0:return dict(attendance=0,occupancy_bps=0,ticket_price=p['ticket_price'],gross=0,capacity=capacity)
 if occupancy_percent is not None:
  if type(occupancy_percent) is not int or not 0<=occupancy_percent<=100:raise ValueError('Percentual de público inválido')
  occupancy=occupancy_percent*100;attendance=(capacity*occupancy_percent+50)//100
 else:
  occupancy=max(p['occupancy_min_bps'],min(p['occupancy_max_bps'],3500+prestige*200))
  attendance=capacity*occupancy//10000
 return dict(attendance=attendance,occupancy_bps=occupancy,ticket_price=p['ticket_price'],gross=attendance*p['ticket_price'],capacity=capacity)

def ticket_operation_cost(gross,policy=None):
 """Estimated direct matchday costs; no exchange rate or second budget debit."""
 return max(0,int(gross))*rules(policy)['match_cost_bps']//10000

def upgrade(book,today,context,policy):
 """Prospective only: never reprice paid entries, old matches or elapsed months."""
 if book.get('schema',1)==1:
  book.update(schema=2,expanded_start=today,rules=deepcopy(policy))
  for key in SWITCHES:
   if key not in book['settings']:
    book['settings'][key]=True
  book['settings_history'].append(dict(date=today,values={k:True for k in SWITCHES[5:]}))
  profiles={p['root']:p for p in context['competitions']}
  for contract in book['agreements'].values():
   if contract['season']==context['season'] and contract['root'] in profiles:
    revised=agreement(profiles[contract['root']],contract['season'],today,policy)
    contract['revisions']=[dict(start=today,per_match=revised['per_match'],rules=revised['rules'])]
 signature=economy_signature(context)
 if book.get('economy_version',0)<3 or list(book.get('economy_profile',()))!=signature:
  start=packed(parse_date(today)+timedelta(days=1))
  profiles={p['root']:p for p in context['competitions']}
  for contract in book['agreements'].values():
   if contract['season']==context['season'] and contract['root'] in profiles:
    revised=agreement(profiles[contract['root']],contract['season'],start,policy,context.get('club_profile'))
    contract.setdefault('revisions',[]).append(dict(start=start,per_match=revised['per_match'],rules=revised['rules'],club_profile=deepcopy(context.get('club_profile',{}))))
  book.setdefault('commercial',{})[str(start)]=dict(start=start,**commercial(context,policy))
  book['economy_version']=3;book['economy_profile']=signature
 book.setdefault('commercial',{})
 key=str(context['season'])
 if key not in book['commercial']:
  book['commercial'][key]=dict(start=max(book['expanded_start'],context['season']),**commercial(context,policy))
 # Some imported agreements already use schema 2 but predate match costs.
 # Version only the absent field from the next day; explicit SQL zero/custom
 # rates and all historical terms/postings remain unchanged.
 for contract in book['agreements'].values():
  terms=match_terms(contract,today)
  if 'match_cost_bps' in terms['rules']:continue
  if any(r['start']>today and 'match_cost_bps' in r.get('rules',{}) for r in contract.get('revisions',[])):continue
  contract.setdefault('revisions',[]).append(dict(start=packed(parse_date(today)+timedelta(days=1)),per_match=terms['per_match'],rules={**terms['rules'],'match_cost_bps':policy['match_cost_bps']}))

def match_terms(contract,day):
 result=contract
 for row in sorted(contract.get('revisions',[]),key=lambda r:r['start']):
  if row['start']<=day:result={**contract,**row}
 return result

def apply(state,*,club,today,budget,context,policy=None):
 """Pure proposal; no files, RAM writes, random draws or wall-clock dates."""
 parse_date(today)
 if state['club']!=club or context['club']!=club or context['date']!=today or today<state['last_date']:raise ValueError('Contexto financeiro divergente')
 if not 0<=budget<=MAX_BUDGET:raise ValueError('Orçamento financeiro inválido')
 result=deepcopy(state);book=result.get('finance');policy=rules(policy)
 if book is None:book=result['finance']=initial(club,today,context,policy)
 if book['club']!=club or today<book['last_date']:raise ValueError('Restaure o histórico financeiro do save carregado')
 upgrade(book,today,context,policy)
 if book['payroll'][-1]['wage']!=context['coach_wage']:
  book['payroll'].append(dict(date=today,wage=context['coach_wage']))
 season=context['season'];book['season']=season
 for profile in context['competitions']:
  key=f"{season}:{profile['root']}"
  if key not in book['agreements']:book['agreements'][key]=agreement(profile,season,today,policy,context.get('club_profile'))
 known={e['id'] for e in book['entries']};original=set(known);baseline=set(book['baseline'])
 proposed=[]
 for match in context['fixtures']:
  if not match['played'] or not max(book['start'],season)<=match['date']<=today or club not in (match['home'],match['away']):continue
  identity=fixture_key(season,match);contract=book['agreements'].get(f"{season}:{match['root']}")
  if identity in baseline or not contract:continue
  terms=match_terms(contract,match['date'])
  categories=[('tv',terms['per_match'],{})]
  if 'tickets:'+identity not in original and match['home']==club and not match.get('neutral',False) and context.get('capacity',0)>0:
   # A captured crowd decision belongs to this fixture only. Unobserved
   # calendar simulations carry their own pre-match reconstructed estimate.
   p=terms['rules'];prestige=int(terms.get('club_profile',context.get('club_profile',{})).get('prestige') or contract['prestige'])
   reading=book.get('attendance',{}).get(identity)
   if reading and any(reading.get(k)!=match[k] for k in ('date','home','away')):reading=None
   reading=reading or match.get('attendance')
   percent=reading.get('percent') if reading else None
   gate=ticket_projection((reading or {}).get('capacity') or context['capacity'],prestige,p,
                         terms.get('club_profile',context.get('club_profile')),occupancy_percent=percent)
   if reading:
    gate.update(crowd_source=reading['source'],crowd_percent=percent,crowd_observed_date=reading.get('observed_date'),crowd_actual=bool(reading.get('actual')))
    book.setdefault('attendance',{})[identity]=dict(reading,id=match['id'],root=match['root'],date=match['date'],home=match['home'],away=match['away'],capacity=gate['capacity'])
   gross=gate['gross'];cost=gross*p.get('match_cost_bps',0)//10000
   categories.append(('tickets',gross,dict(**gate,estimated=True,match_cost=cost)))
   # An old posted ticket receipt must never acquire a new retroactive debit.
   if cost and 'tickets:'+identity not in original:categories.append(('match_costs',-cost,dict(gross=gross,estimated=True)))
  for kind,amount,detail in categories:
   key=kind+':'+identity
   if key not in known:
    proposed.append(dict(id=key,kind=kind,date=match['date'],amount=amount,status='pending',
     description=contract['name'],fixture=match['id'],agreement=contract['id'],home=match['home'],away=match['away'],
     home_name=match.get('home_name','Clube '+str(match['home'])),away_name=match.get('away_name','Clube '+str(match['away'])),competition_asset=contract['asset'],**detail))
    known.add(key)
 # Month-end liability; first month counts only enabled days after activation.
 cursor=parse_date(book['start']).replace(day=1);end=parse_date(today)
 while cursor<=end:
  last=cursor.replace(day=monthrange(cursor.year,cursor.month)[1]);due=packed(last);key=f'coach:{cursor.year}{cursor.month:02d}'
  if due<=today and key not in known:
   amount=0;missing=False;enabled_days=0
   for n in range(1,last.day+1):
    day=packed(cursor.replace(day=n))
    if day<book['start'] or not active(book,'coach',day):continue
    wage=next((r['wage'] for r in reversed(book['payroll']) if r['date']<=day),None)
    if wage is None:missing=True;break
    amount+=wage*52;enabled_days+=1
   if not missing:
    amount=(amount+6*last.day)//(12*last.day)
    proposed.append(dict(id=key,kind='coach',date=due,amount=-amount,status='pending',
     description='Salário do técnico',enabled_days=enabled_days,month_days=last.day))
    known.add(key)
  for kind in ('sponsor','staff'):
   key=f'{kind}:{cursor.year}{cursor.month:02d}'
   if due>today or key in known or due<book['expanded_start']:continue
   days=0;annual_days=0
   for n in range(1,last.day+1):
    day=packed(cursor.replace(day=n))
    allocations=[v for v in book['commercial'].values() if v['start']<=day]
    if not allocations or not active(book,kind,day):continue
    allocation=max(allocations,key=lambda v:v['start']);days+=1;annual_days+=allocation[kind+'_annual']
   amount=(annual_days+6*last.day)//(12*last.day)
   proposed.append(dict(id=key,kind=kind,date=due,amount=amount if kind=='sponsor' else -amount,status='pending',
    description='Patrocínio do clube' if kind=='sponsor' else 'Comissão técnica',enabled_days=days,month_days=last.day,estimated=True))
   known.add(key)
  cursor=(last+timedelta(days=1)).replace(day=1)
 book['entries'].extend(proposed);events=[]
 indexed={e['id']:e for e in book['entries']}
 for entry in sorted(book['entries'],key=lambda e:(e['date'],0 if e['amount']>=0 else 1,e['id'])):
  if entry['status']!='pending':continue
  kind=entry['kind']
  # Match earnings disabled on the event day are permanently skipped, never
  # accumulated and credited after re-enabling. Existing debts are retained.
  if kind in ('tv','tickets','match_costs') and not active(book,kind,entry['date']):
   entry['status']='disabled';continue
  if kind=='match_costs' and not active(book,'tickets',entry['date']):entry['status']='disabled';continue
  if kind=='match_costs' and indexed.get('tickets:'+entry['id'].split(':',1)[1],{}).get('status')!='applied':continue
  if kind in MONTHLY_KINDS and not entry['amount']:entry['status']='disabled';continue
  if not active(book,kind,today):continue
  after=budget+entry['amount']
  if not 0<=after<=MAX_BUDGET:continue
  budget=after;entry.update(status='applied',paid_date=today)
  events.append(dict(event='finance',id=entry['id'],kind=kind,amount=entry['amount'],date=entry['date'],paid_date=today))
 book['last_date']=today
 result['last_date']=today
 return result,budget,events

def monthly(state,*,settlement=False):
 """Cash totals are derived, never another payment trigger."""
 result={}
 def add(day,kind,amount):
  row=result.setdefault(day//100,dict(month=day//100,tv=0,tickets=0,coach=0,sponsor=0,staff=0,match_costs=0,loans=0,loan_credit=0,interest=0))
  row[kind]+=amount
 for e in state.get('finance',{}).get('entries',[]):
  if e['status']=='applied':add(e['paid_date'] if settlement else e['date'],e['kind'],e['amount'])
 for contract in state['contracts']:
  add(contract['date'],'loan_credit',contract['principal'])
  for p in contract['payments'][:contract['paid']]:
   add(p['paid_date'] if settlement else p['date'],'loans',-p['amount']);add(p['paid_date'] if settlement else p['date'],'interest',-p['interest'])
 for row in result.values():
  row['income']=row['tv']+row['tickets']+row['sponsor'];row['expenses']=-row['coach']-row['staff']-row['match_costs']-row['loans']
  row['cash_result']=row['income']+row['loan_credit']-row['expenses']
  row['operating_result']=row['income']+row['coach']+row['staff']+row['match_costs']+row['interest']
 return sorted(result.values(),key=lambda r:r['month'],reverse=True)


def cash_delta(events):
 """Signed native-budget effect of a journal batch, excluding unpaid arrears."""
 result=0
 for e in events:
  if e['event'] in ('credit','finance'):result+=e['amount']
  elif e['event'] in ('installment','manual_installment'):result-=e['amount']
 return result


def record_attendance(state,reading,today):
 """Capture the next fixture without moving money or editing paid history."""
 book=state.get('finance')
 if not book or not reading or reading['date']<today or state['club'] not in (reading['home'],reading['away']):return state,False
 if type(reading.get('percent')) is not int or not 0<=reading['percent']<=100:raise ValueError('Percentual de público inválido')
 identity=fixture_key(book['season'],reading)
 if any(e['id']=='tickets:'+identity for e in book['entries']):return state,False
 previous=book.get('attendance',{}).get(identity)
 if previous and previous.get('actual') and not reading.get('actual'):return state,False
 if previous==reading:return state,False
 result=deepcopy(state);result['finance'].setdefault('attendance',{})[identity]=dict(reading)
 return result,True
