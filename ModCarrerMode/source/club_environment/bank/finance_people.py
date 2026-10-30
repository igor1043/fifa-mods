"""Read-only player finance projections. No budget or contract mutations."""

def payroll_rows(roster,contracts,expiry=None):
 """Only current squad members; duplicate/absent wages remain unknown."""
 grouped={}
 for row in contracts:grouped.setdefault(row['playerid'],[]).append(row)
 result=[]
 for p in roster:
  rows=grouped.get(p['id'],[]);wage=rows[0].get('wage') if len(rows)==1 else None
  if type(wage) is not int or not 0<=wage<100_000_000:wage=None
  result.append(dict(id=p['id'],name=p['name'],position=p['position'],overall=p['overall'],
   age=p.get('age',-1),number=p.get('number'),starter=p.get('starter',-1),
   weekly=wage,monthly=(wage*52+6)//12 if wage is not None else None,
   annual=wage*52 if wage is not None else None,expiry=(expiry or {}).get(p['id'])))
 return sorted(result,key=lambda p:(p['weekly'] is None,-(p['weekly'] or 0),p['name']))

def club_transfers(payload,club,season,today):
 def date(row):
  try:return int(str(row.get('date','')).replace('-','')[:8])
  except (TypeError,ValueError):return 0
 # The shared market reader already requires completed offers and verifies
 # destination membership. Preserve those rules rather than counting bids.
 result=[]
 for row in payload.get('transfers',[]):
  source=row.get('from',{});target=row.get('to',{})
  if club not in (source.get('id'),target.get('id')) or not season<=date(row)<=today:continue
  result.append(dict(id=row['id'],player=row['playerId'],name=row['playerName'],
   date=date(row),fee=max(0,int(row['fee'])),loan=bool(row['loan']),
   direction='in' if target.get('id')==club else 'out',
   other=source if target.get('id')==club else target))
 return sorted(result,key=lambda r:(r['date'],str(r['id'])),reverse=True)

def debts(contracts,banks):
 result=[]
 for c in contracts:
  remaining=c['payments'][c['paid']:];bank=c['bank']
  result.append(dict(id=c['id'],bank=banks[bank]['name'],bank_id=banks[bank]['id'],principal=c['principal'],date=c['date'],
   paid=c['paid'],total=len(c['payments']),balance=sum(p['amount'] for p in remaining),
   next_date=remaining[0]['date'] if remaining else None,
   next_amount=remaining[0]['amount'] if remaining else 0))
 return result
