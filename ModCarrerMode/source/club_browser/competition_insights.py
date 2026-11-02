"""Competition-only highlights from dated played fixtures, never predictions."""
from collections import defaultdict


def build(fixtures,today,statistics,teams,cup=False):
    unique={}
    for m in fixtures:
        if not m.get('played') or m['date']>today:continue
        h,a=m.get('homeScore'),m.get('awayScore')
        if type(h) is not int or type(a) is not int or min(h,a)<0:continue
        if min(m['home'],m['away'])<=0 or m['home']==m['away']:continue
        unique[m['id']]=m
    totals=defaultdict(lambda:dict(games=0,gf=0,ga=0))
    for m in unique.values():
        for club,gf,ga in ((m['home'],m['homeScore'],m['awayScore']),(m['away'],m['awayScore'],m['homeScore'])):
            t=totals[club];t['games']+=1;t['gf']+=gf;t['ga']+=ga
    def team(club):return dict(club=club,name=teams.get(club,'Clube'),**totals[club])
    result={}
    from competition_campaign import depth,minimum_sample
    progression=depth(list(unique.values())) if cup else {}
    if totals:
        maximum=max(t['games'] for t in totals.values())
        minimum=minimum_sample(maximum) if cup else max(1,(maximum+1)//2)
        eligible=[c for c,t in totals.items() if t['games']>=minimum]
        if cup:
            latest=max(progression.get(c,0) for c in eligible)
            eligible=[c for c in eligible if progression.get(c,0)==latest]
        result['defense']=team(min(eligible,key=lambda c:(totals[c]['ga']/totals[c]['games'],totals[c]['ga'],-totals[c]['games'],c)))
        result['attack']=team(max(totals,key=lambda c:(totals[c]['gf'],totals[c]['gf']/totals[c]['games'],-c)))
        result['defense']['minimumGames']=minimum
    wins=[m for m in unique.values() if m['homeScore']!=m['awayScore']]
    if wins:
        m=max(wins,key=lambda m:(abs(m['homeScore']-m['awayScore']),max(m['homeScore'],m['awayScore']),-m['date'],-m['id']))
        result['biggestWin']={k:m.get(k) for k in ('id','date','home','away','homeName','awayName','homeScore','awayScore','stageKind')}
    for key,field in (('scorer','goals'),('assists','assists')):
        if statistics.get(field):result[key]=statistics[field][0]
    if statistics.get('goalkeeper'):result['goalkeeper']=statistics['goalkeeper']
    if cup and statistics.get('goalkeepers'):
        candidates=statistics['goalkeepers'];minimum=minimum_sample(max(p['appearances'] for p in candidates))
        candidates=[p for p in candidates if p['appearances']>=minimum and p['club'] in progression]
        if candidates:
            latest=max(progression[p['club']] for p in candidates)
            candidates=[p for p in candidates if progression[p['club']]==latest]
            best=max(candidates,key=lambda p:((p['averageRating']*p['appearances']+6*4)/(p['appearances']+4),p['appearances'],-p['id']))
            result['goalkeeper']=dict(best,minimumAppearances=minimum,selection='campaign-depth-and-sample')
    return result
