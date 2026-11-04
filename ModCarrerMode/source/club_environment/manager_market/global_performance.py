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
 # Parent/child overlap is local to one club and one competition root.
 # Scanning every retained row for every standing made each calendar day
 # quadratic across thousands of unrelated clubs/competitions.
 retained_by_club=defaultdict(list)
 for order,(r,rt) in enumerate(sorted(all_rows,key=lambda pair:len(ancestry(pair[0][1])),reverse=True)):
  identity=(r[2],rt[0]);retained=retained_by_club[identity]
  children=[pair for pair in retained if r[1] in ancestry(pair[0][1])[1:]]
  if children:
   if r[9]<=sum(pair[0][9] for pair in children):continue
   retained_by_club[identity]=retained=[pair for pair in retained if pair not in children]
  retained.append((r,rt,order))
 retained=[(r,rt) for r,rt,_ in sorted((pair for pairs in retained_by_club.values() for pair in pairs),key=lambda p:p[2])]
 performance=[];groups=defaultdict(list);seen=set()
 for r,rt in retained:
  ident=(rt[0],r[1],r[2])
  if ident in seen:continue
  seen.add(ident);row=dict(key=f'fce:{rt[0]}:{r[1]}',root=rt[0],asset=rt[3],group=r[1],club=r[2],date=today,season=season,source='fce',**dict(zip(WDL,r[3:9])))
  row['played']=r[9];performance.append(row);groups[(rt[3],r[1])].append(row)
  goals=snapshot.get('standingGoals',{}).get(str(r[0]))
  if goals is not None and len(goals)==4 and all(type(v)==int and v>=0 for v in goals):row.update(zip(('hgf','hga','agf','aga'),goals))
 tables={};dates={};club_tables={};members_by_league=defaultdict(set);links_by_league=defaultdict(list);groups_by_asset=defaultdict(list);fixtures_by_asset=defaultdict(list)
 for club,lid in memberships.items():members_by_league[lid].add(club)
 for row in links:
  if row.get('secondarytable')==0:links_by_league[row.get('leagueid')].append(row)
 for (asset,_),rows in groups.items():groups_by_asset[asset].append(rows)
 for match in fixtures:
  if match['played'] and match['date']<=today:fixtures_by_asset[match['asset']].append(match)
 for lid in set(memberships.values()):
  members=members_by_league[lid];options=[rs for rs in groups_by_asset[lid] if len({r['club'] for r in rs}&members)>=min(2,len(members)) and any(r['played'] for r in rs)]
  represented={r['club'] for rs in options for r in rs}&members
  league_rows=[r for r in links_by_league[lid] if r.get('teamid') in members]
  native_played=sum(r.get('nummatchesplayed',0) for r in league_rows)
  fce_played=sum(r['played'] for rs in options for r in rs if r['club'] in members)
  # A partial FCE publication must not hide a complete league table.
  if options and native_played>0 and {r['teamid'] for r in league_rows}==members and (represented!=members or native_played>fce_played):
   options=[]
  if options:
   # Ignore empty setup groups. Multi-group leagues retain each club's group;
   # group A's rank must not be compared with every team in groups B..H.
   options.sort(key=lambda rs:(len({r['club'] for r in rs}&members),sum(r['played'] for r in rs)),reverse=True)
   detailed=defaultdict(list)
   for match in fixtures_by_asset[lid]:
    detailed[match['home']].append(match);detailed[match['away']].append(match)
   for chosen in options:
    table=[dict(club=r['club'],played=r['played'],points=(r['hw']+r['aw'])*3+r['hd']+r['ad'],wins=r['hw']+r['aw'],gf=r.get('hgf',0)+r.get('agf',0),ga=r.get('hga',0)+r.get('aga',0)) for r in chosen if r['club'] in members]
    for row in table:
     own=detailed[row['club']]
     if len(own)==row['played']:
      row['gf']=sum(m['hg'] if row['club']==m['home'] else m['ag'] for m in own);row['ga']=sum(m['ag'] if row['club']==m['home'] else m['hg'] for m in own)
    table=rank(table);tables.setdefault(str(lid),table);dates[str(lid)]=today
    for row in table:club_tables.setdefault(str(row['club']),table)
  else:
   # FIFA simulates some leagues only in leagueteamlinks, without fixtures.
   # This evidence retains the save's date; it is never labelled as live RAM.
   table=[]
   for r in league_rows:
    values=[r.get(k) for k in ('homewins','homedraws','homelosses','awaywins','awaydraws','awaylosses')]
    if any(type(v)!=int or not 0<=v<=255 for v in values):continue
    # Expanded leagues can retain a zero summary field while their six W/D/L
    # counters and points are current. Require both football totals to agree.
    if r.get('nummatchesplayed') not in (0,sum(values)):continue
    hw,hd,hl,aw,ad,al=values;count=sum(values)
    if r.get('points')!=3*(hw+aw)+hd+ad:continue
    performance.append(dict(key='db:'+str(lid),root=0,asset=lid,group=lid,club=r['teamid'],date=saved_date,season=season,source=league_source,played=count,**dict(zip(WDL,values))))
    table.append(dict(club=r['teamid'],played=count,points=3*(hw+aw)+hd+ad,wins=hw+aw,gf=max(0,r.get('homegf',0))+max(0,r.get('awaygf',0)),ga=max(0,r.get('homega',0))+max(0,r.get('awayga',0))))
   if len(table)>=2 and any(r['played'] for r in table):
    tables[str(lid)]=rank(table);dates[str(lid)]=saved_date
    for row in table:club_tables[str(row['club'])]=table
 # Native FCE and league rows describe the same campaign; retain the most
 # complete source independently for each club, including partial groups.
 candidates=defaultdict(lambda:defaultdict(list))
 for r in performance:candidates[(r['asset'],r['club'])]['fce' if r['root'] else 'league'].append(r)
 performance=[]
 for sources in candidates.values():
  fce=sources.get('fce',[]);league=sources.get('league',[])
  performance.extend(fce if fce and sum(r['played'] for r in fce)>=sum(r['played'] for r in league) else league)
 return dict(performance=performance,tables=tables,club_tables=club_tables,table_dates=dates,coverage=dict(competitions=len({r['asset'] for r in performance}),live_competitions=len({r['asset'] for r in performance if r['source'] in ('fce','live_league')}),leagues_with_tables=len(tables),live_league_tables=sum(d==today for d in dates.values()),live_database=league_source=='live_league',clubs_with_tables=len(club_tables),clubs_with_games=len({r['club'] for r in performance if r['played']}),detailed_matches=sum(m['played'] and m['date']<=today for m in fixtures)))

def rank(rows):
 rows.sort(key=lambda r:(-r['points'],-r.get('wins',0),-(r['gf']-r['ga']),-r['gf'],r['club']))
 for i,r in enumerate(rows,1):r['rank']=i+1
 return rows
