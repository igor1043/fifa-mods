"""Global FCE counters plus saved league summaries; never fabricate fixtures."""
from collections import defaultdict

WDL=('hw','hd','hl','aw','ad','al')

def project(snapshot,fixtures,memberships,links,saved_date,season,today,league_source='saved_league'):
 nodes={r[0]:r for r in snapshot.get('nodes',[]) if len(r)==5};cache={}
 def ancestry(ident):
  if ident in cache:return cache[ident]
  out=[];seen=set()
  while ident in nodes and ident not in seen:
   seen.add(ident);out.append(ident);ident=nodes[ident][1]
  cache[out[0] if out else ident]=out;return out
 def root(ident):return next((nodes[i] for i in ancestry(ident) if nodes[i][2]==3),None)
 all_rows=[];by_club=defaultdict(set)
 for r in snapshot.get('standings',[]):
  if len(r)!=10 or any(type(v)!=int for v in r) or r[2] not in memberships or min(r[3:])<0 or max(r[3:9])>255 or sum(r[3:9])!=r[9]:continue
  rt=root(r[1])
  if not rt or rt[3]<=0:continue
  all_rows.append((r,rt));by_club[r[2]].add(r[1])
 performance=[];groups=defaultdict(list);seen=set()
 for r,rt in all_rows:
  # Some providers also publish a root/phase aggregate. Keep the leaf once.
  if any(r[1] in ancestry(other)[1:] for other in by_club[r[2]] if other!=r[1]):continue
  ident=(rt[0],r[1],r[2])
  if ident in seen:continue
  seen.add(ident);row=dict(key=f'fce:{rt[0]}:{r[1]}',root=rt[0],asset=rt[3],group=r[1],club=r[2],date=today,season=season,source='fce',**dict(zip(WDL,r[3:9])))
  row['played']=r[9];performance.append(row);groups[(rt[3],r[1])].append(row)
 tables={};dates={};club_tables={}
 for lid in set(memberships.values()):
  members={t for t,l in memberships.items() if l==lid};options=[rs for (asset,_),rs in groups.items() if asset==lid and len({r['club'] for r in rs}&members)>=min(2,len(members)) and any(r['played'] for r in rs)]
  if options:
   # Ignore empty setup groups. Multi-group leagues retain each club's group;
   # group A's rank must not be compared with every team in groups B..H.
   options.sort(key=lambda rs:(len({r['club'] for r in rs}&members),sum(r['played'] for r in rs)),reverse=True)
   detailed=[m for m in fixtures if m['asset']==lid and m['played'] and m['date']<=today]
   for chosen in options:
    table=[dict(club=r['club'],played=r['played'],points=(r['hw']+r['aw'])*3+r['hd']+r['ad'],wins=r['hw']+r['aw'],gf=0,ga=0) for r in chosen if r['club'] in members]
    for row in table:
     own=[m for m in detailed if row['club'] in (m['home'],m['away'])]
     if len(own)==row['played']:
      row['gf']=sum(m['hg'] if row['club']==m['home'] else m['ag'] for m in own);row['ga']=sum(m['ag'] if row['club']==m['home'] else m['hg'] for m in own)
    table=rank(table);tables.setdefault(str(lid),table);dates[str(lid)]=today
    for row in table:club_tables.setdefault(str(row['club']),table)
  else:
   # FIFA simulates some leagues only in leagueteamlinks, without fixtures.
   # This evidence retains the save's date; it is never labelled as live RAM.
   table=[]
   for r in links:
    if r.get('secondarytable')!=0 or r.get('leagueid')!=lid or r.get('teamid') not in members:continue
    values=[r.get(k) for k in ('homewins','homedraws','homelosses','awaywins','awaydraws','awaylosses')]
    if any(type(v)!=int or not 0<=v<=255 for v in values) or sum(values)!=r.get('nummatchesplayed'):continue
    hw,hd,hl,aw,ad,al=values;count=sum(values)
    if r.get('points')!=3*(hw+aw)+hd+ad:continue
    performance.append(dict(key='db:'+str(lid),root=0,asset=lid,group=lid,club=r['teamid'],date=saved_date,season=season,source=league_source,played=count,**dict(zip(WDL,values))))
    table.append(dict(club=r['teamid'],played=count,points=3*(hw+aw)+hd+ad,wins=hw+aw,gf=max(0,r.get('homegf',0))+max(0,r.get('awaygf',0)),ga=max(0,r.get('homega',0))+max(0,r.get('awayga',0))))
   if len(table)>=2 and any(r['played'] for r in table):
    tables[str(lid)]=rank(table);dates[str(lid)]=saved_date
    for row in table:club_tables[str(row['club'])]=table
 return dict(performance=performance,tables=tables,club_tables=club_tables,table_dates=dates,coverage=dict(competitions=len({r['asset'] for r in performance}),live_competitions=len({r['asset'] for r in performance if r['source'] in ('fce','live_league')}),leagues_with_tables=len(tables),live_league_tables=sum(d==today for d in dates.values()),live_database=league_source=='live_league',clubs_with_tables=len(club_tables),clubs_with_games=len({r['club'] for r in performance if r['played']}),detailed_matches=sum(m['played'] and m['date']<=today for m in fixtures)))

def rank(rows):
 rows.sort(key=lambda r:(-r['points'],-r.get('wins',0),-(r['gf']-r['ga']),-r['gf'],r['club']))
 for i,r in enumerate(rows,1):r['rank']=i+1
 return rows
