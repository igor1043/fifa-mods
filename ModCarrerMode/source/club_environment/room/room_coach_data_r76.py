"""Read-only presentation data, using the shared career result evidence."""
from collections import defaultdict
from pathlib import Path
import sys


def build(context, snapshot, roster, rows, game, saved_tables):
    # The native publication already belongs to the validated active save.
    # Join its derived counters by slot + competition + club, never by name.
    snapshot=dict(snapshot);slots={r[0]:r for r in snapshot.get('standings',[]) if len(r)==10}
    goals=dict(snapshot.get('standingGoals',{}))
    for r in snapshot.get('derivedStandings',[]):
        old=slots.get(r[0]) if r else None
        if len(r)==14 and old and r[1:3]==old[1:3] and min(r)>=0 and sum(r[3:9])==r[9]:
            slots[r[0]]=r[:10];goals[str(r[0])]=r[10:14]
    snapshot['standings']=list(slots.values());snapshot['standingGoals']=goals
    # Use the same fixture/aggregate reconciliation as the team/coach screens.
    browser=Path(game)/'ModCarrerMode/source/club_browser'
    if str(browser) not in sys.path:sys.path.append(str(browser))
    from career_results import summaries, club_stats, FIELDS
    nodes={r[0]:r for r in snapshot.get('nodes',[]) if len(r)==5}
    def root(node):
        seen=set()
        while node in nodes and node not in seen:
            seen.add(node);r=nodes[node]
            if r[2]==3:return r[0],r[3]
            node=r[1]
        return None
    links=[]
    for r in rows('leagueteamlinks'):
        d={k:r.value(k) for k in FIELDS if k in r.fields}
        if all(k in d for k in ('teamid','leagueid','secondarytable')):links.append(d)
    memberships={r['teamid']:r['leagueid'] for r in links if r['secondarytable']==0}
    # Base membership is useful; base results must never become career results.
    if 'leagueteamlinks' not in saved_tables:
        links=[{**r,**dict.fromkeys(FIELDS[3:],0)} for r in links]
    schedule=[]
    for r in snapshot.get('fixtures',[]):
        if len(r)<10:continue
        comp=root(r[1])
        if not comp:continue
        schedule.append(dict(id=r[0],root=comp[0],asset=comp[1],date=r[3],home=r[5],away=r[6],
            played=bool(r[9] and 0<=r[7]<100 and 0<=r[8]<100),homeScore=r[7],awayScore=r[8]))
    calendar=rows('career_calendar')
    season=calendar[0].value('startdate') if len(calendar)==1 and 'startdate' in calendar[0].fields else context['date']//10000*10000+101
    evidence=summaries(snapshot,schedule,memberships,links,snapshot['date'],season,context['date'])
    club=context['club'];stats=club_stats(evidence,club)
    team_names={r.value('teamid'):r.value('teamname') for r in rows('teams')}
    league=memberships.get(club,context['league']);table=evidence.get('club_tables',{}).get(str(club),[])
    table=[dict(r,name=team_names.get(r['club'],'Clube'),rank=i+1,
                draws=max(0,r['points']-3*r['wins']),losses=max(0,r['played']-r['wins']-(r['points']-3*r['wins']))) for i,r in enumerate(table)]
    players={r.value('playerid'):r for r in rows('players')}
    unique={}
    for r in snapshot.get('stats',[]):
        if len(r)<10 or r[2]!=club or r[3] not in players or min(r[4:8])<0:continue
        key=r[1],r[3]
        if key not in unique or (r[4],r[5],r[0])>(unique[key][4],unique[key][5],unique[key][0]):unique[key]=r
    totals=defaultdict(lambda:dict(games=0,goals=0,assists=0,ratingSum=0,ratedGames=0))
    for r in unique.values():
        d=totals[r[3]];d['games']+=r[4];d['goals']+=r[6];d['assists']+=r[7]
        if r[9]==3 and r[4]>0 and 10*r[4]<=r[8]<=100*r[4]:d['ratingSum']+=r[8];d['ratedGames']+=r[4]
    squad=[];now=context['date']//10000
    for p in roster:
        record=players.get(p['id'])
        def value(key,default=0):return record.value(key) if record and key in record.fields else default
        d=dict(p,overall=value('overallrating'),potential=value('potential'),position=value('preferredposition1'),
               contract=value('contractvaliduntil'),**totals[p['id']])
        d['rating']=round(d['ratingSum']/(10*d['ratedGames']),1) if d['ratedGames'] else None
        squad.append(d)
    own=[dict(m,home=m['home']==club,gf=m['homeScore'] if m['home']==club else m['awayScore'],
              ga=m['awayScore'] if m['home']==club else m['homeScore']) for m in schedule if club in (m['home'],m['away']) and m['played'] and season<=m['date']<=context['date']]
    own.sort(key=lambda m:(m['date'],m['id']))
    groups=defaultdict(list)
    for p in squad:
        pos=p['position'];label='Goleiros' if pos==0 else 'Defensores' if pos<=8 else 'Meio-campo' if pos<=19 else 'Ataque'
        groups[label].append(p)
    coverage=[dict(name=k,count=len(v),overall=round(sum(p['overall'] for p in v)/len(v),1)) for k,v in groups.items()]
    from competition_names_r57 import competition_name
    return dict(stats=stats,table=table,league=league,leagueName=competition_name(league,rows),season=season,recent=own[-8:],squad=squad,
                coverage=coverage,contracts=[p for p in squad if now<=p['contract']<=now+1],
                tableDate=evidence.get('table_dates',{}).get(str(league)),source='shared_career_results')
