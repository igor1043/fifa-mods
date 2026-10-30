"""Read-only shared result evidence: fixtures plus FIFA's aggregate standings.

Simulated foreign leagues do not always retain a fixture per match. Aggregate
rows are evidence, never a licence to invent an opponent, score or match date.
"""
from collections import defaultdict
from pathlib import Path
import time

WDL=('hw','hd','hl','aw','ad','al')
FIELDS=('teamid','leagueid','secondarytable','homewins','homedraws','homelosses',
        'awaywins','awaydraws','awaylosses','nummatchesplayed','points',
        'homegf','homega','awaygf','awayga','currenttableposition')

def live_leagues(game,saved,profile,today,wait=.6):
    import prepared_views
    from manager_market.live_leagues import read
    root=Path(game)/'ModCarrerMode/runtime/manager_market'
    try:
        prepared_views.publish(root/'read_request.tsv',saved,profile,today,'0'*64)
        deadline=time.monotonic()+wait
        while True:
            try:result=read(root/'live_leagues.tsv',dict(save=saved,profile=profile,date=today),prepared_views.ticks())
            except (OSError,ValueError,KeyError,UnicodeError):result=None
            if result or time.monotonic()>=deadline:return result
            time.sleep(.05)
    except OSError:return None

def summaries(snapshot,schedule,memberships,links,saved_date,season,today,live=False):
    from manager_market.global_performance import project
    fixtures=[dict(m,hg=m.get('homeScore'),ag=m.get('awayScore')) for m in schedule]
    publication=project(snapshot,fixtures,memberships,links,saved_date,season,today,'live_league' if live else 'saved_league')
    # A partially published FCE league can also fall back to leagueteamlinks.
    # Those are two views of the SAME campaign, not additional matches. Keep
    # the most complete counter set per club/competition, never sum the two.
    candidates=defaultdict(lambda:defaultdict(list))
    for p in publication['performance']:
        candidates[(p['asset'],p['club'])]['fce' if p['source']=='fce' else 'league'].append(p)
    selected=[]
    for sources in candidates.values():
        native=sources.get('fce',[]);league=sources.get('league',[])
        count=lambda rows:sum(sum(r[k] for k in WDL) for r in rows)
        selected.extend(native if native and count(native)>=count(league) else league)
    publication['performance']=selected
    out={};details=defaultdict(list);seen=set()
    for m in schedule:
        if not m.get('played') or not season<=m['date']<=today or any(type(m.get(k))!=int or not 0<=m[k]<100 for k in ('homeScore','awayScore')):continue
        identity=(m['date'],m['root'],m['id'])
        if identity in seen:continue
        seen.add(identity)
        for home,club in ((True,m['home']),(False,m['away'])):
            details[(m['asset'],club)].append(dict(date=m['date'],home=home,gf=m['homeScore'] if home else m['awayScore'],ga=m['awayScore'] if home else m['homeScore']))
    for p in publication['performance']:
        if p['date']>today:continue
        key=p['asset'],p['club'];r=out.setdefault(key,dict(asset=p['asset'],club=p['club'],date=p['date'],sources=set(),**dict.fromkeys(WDL,0)))
        for k in WDL:r[k]+=p[k]
        r['sources'].add(p['source']);r['date']=max(r['date'],p['date'])
    # Keep detailed-only competitions too; they must not disappear in a fallback.
    for key,matches in details.items():
        d=dict.fromkeys(WDL,0)
        for m in matches:d[('h' if m['home'] else 'a')+('w' if m['gf']>m['ga'] else 'd' if m['gf']==m['ga'] else 'l')]+=1
        r=out.get(key)
        if r is None or sum(d.values())>sum(r[k] for k in WDL):
            r=dict(asset=key[0],club=key[1],date=max(m['date'] for m in matches),sources={'fixtures'},**d);out[key]=r
        r['detailedGames']=len(matches)
    league_rows={(r['leagueid'],r['teamid']):r for r in links if r.get('secondarytable')==0}
    for key,r in out.items():
        r['games']=sum(r[k] for k in WDL);r['wins']=r['hw']+r['aw'];r['draws']=r['hd']+r['ad'];r['losses']=r['hl']+r['al'];r['points']=3*r['wins']+r['draws'];r['percentage']=round(100*r['points']/(3*r['games']),2) if r['games'] else 0
        matches=details.get(key,[]);r['detailedGames']=len(matches)
        for k in ('goalsFor','goalsAgainst','homeGoalsFor','homeGoalsAgainst','awayGoalsFor','awayGoalsAgainst'):r[k]=-1
        if len(matches)==r['games']:
            r['goalsFor']=sum(m['gf'] for m in matches);r['goalsAgainst']=sum(m['ga'] for m in matches)
            for side in ('home','away'):
                own=[m for m in matches if m['home']==(side=='home')]
                r[side+'GoalsFor']=sum(m['gf'] for m in own);r[side+'GoalsAgainst']=sum(m['ga'] for m in own)
        else:
            league=league_rows.get(key)
            if league and [league.get(k) for k in ('homewins','homedraws','homelosses','awaywins','awaydraws','awaylosses')]==[r[k] for k in WDL] and all(type(league.get(k))==int and league[k]>=0 for k in ('homegf','homega','awaygf','awayga')):
                r.update(homeGoalsFor=league['homegf'],homeGoalsAgainst=league['homega'],awayGoalsFor=league['awaygf'],awayGoalsAgainst=league['awayga'])
                r['goalsFor']=league['homegf']+league['awaygf'];r['goalsAgainst']=league['homega']+league['awayga']
        r['sources']=sorted(r['sources'])
    publication['summaries']=list(out.values())
    return publication

def from_career(game,cache,dbs,base,snapshot,schedule,live=None):
    def rows(name,fields):
        db=next((d for d in dbs if name in d.tables),None)
        return cache.table(db,name,fields) if db else []  # Never use stock league results as a career fallback.
    calendar=rows('career_calendar',['currdate','startdate']);dates=calendar[0] if len(calendar)==1 else dict(currdate=snapshot['date'],startdate=snapshot['date']//10000*10000+101)
    links=live['rows'] if live else rows('leagueteamlinks',FIELDS)
    memberships={r['teamid']:r['leagueid'] for r in links if r.get('secondarytable')==0}
    result=summaries(snapshot,schedule,memberships,links,snapshot['date'] if live else dates['currdate'],dates['startdate'],snapshot['date'],live=bool(live))
    result.update(seasonStart=dates['startdate'],liveRevision=live['revision'] if live else None)
    return result

def club_stats(evidence,club):
    rows=[r for r in evidence['summaries'] if r['club']==club]
    def roll(part):
        keys=('hw','hd','hl') if part=='home' else ('aw','ad','al') if part=='away' else WDL
        w=sum(r[k] for r in rows for k in keys if k.endswith('w'));d=sum(r[k] for r in rows for k in keys if k.endswith('d'));l=sum(r[k] for r in rows for k in keys if k.endswith('l'));games=w+d+l
        prefix='' if part=='total' else part
        goals={}
        for suffix in ('GoalsFor','GoalsAgainst'):
            key=prefix+suffix if prefix else suffix[0].lower()+suffix[1:]
            goals[suffix[0].lower()+suffix[1:]]=sum(r[key] for r in rows) if all(r.get(key,-1)>=0 for r in rows) else -1
        return dict(games=games,wins=w,draws=d,losses=l,points=3*w+d,**goals,percentage=round((3*w+d)*100/(3*games),2) if games else 0)
    result=roll('total');result.update(home=roll('home'),away=roll('away'));return result
