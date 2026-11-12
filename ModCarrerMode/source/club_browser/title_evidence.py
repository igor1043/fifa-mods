"""Confirmed football titles, independent of UI and coach-market simulation."""
def career_start(calendar,user):
    # startdate is reset by FIFA at every season rollover. seasoncount is
    # one-based; retain the career's original season, not just this year's.
    start=int(calendar['startdate']);count=max(1,int(user.get('seasoncount') or 1))
    return (start//10000-count+1)*10000+(start//100%100)*100+1

def season_of(date,start):
    month=max(1,min(12,int(start)//100%100));year=int(date)//10000
    return (year if int(date)%10000>=month*100+1 else year-1)*10000+month*100+1

def merge_scores(saved,snapshot,season):
    nodes={r[0]:r for r in snapshot['nodes']};merged={(m['id'],m['date']):dict(m) for m in saved}
    def root(n):
        seen=set()
        while n in nodes and n not in seen:
            seen.add(n);r=nodes[n]
            if r[2]==3:return r[0],r[3]
            n=r[1]
    by_id={}
    for key in merged:by_id.setdefault(key[0],[]).append(key)
    for f in snapshot['fixtures']:
        if len(f)<10 or f[3]<season or min(f[5:7])<=0 or f[5]==f[6]:continue
        comp=root(f[1])
        if not comp:continue
        key=(f[0],f[3]);old=merged.get(key)
        if old is None:
            for previous in by_id.get(f[0],[]):
                candidate=merged.get(previous)
                # FIFA reuses fixture IDs in later seasons. A completed old
                # match is immutable evidence, not a new year's placeholder.
                if not candidate or candidate.get('played'):continue
                if season_of(candidate['date'],season)==season_of(f[3],season):
                    old=candidate;merged.pop(previous,None)
                break
        same=old and (old['root'],old['home'],old['away'])==(comp[0],f[5],f[6])
        template=old and old.get('schedule_template') and not old.get('played') and (old['root'],old['asset'],old['date'])==(comp[0],comp[1],f[3])
        node=nodes.get(f[2])
        if node and node[2]==5:node=nodes.get(node[1])
        stage=old['stage'] if same or template else node[0] if node and node[2]==4 else f[2]
        kind=old['stageKind'] if same or template else (node[4] if node and node[2]==4 else 0)
        merged[key]=dict(id=f[0],root=comp[0],asset=comp[1],stage=stage,stageKind=kind,
            date=f[3],home=f[5],away=f[6],homeScore=f[7] if f[9]==1 else None,
            awayScore=f[8] if f[9]==1 else None,played=f[9]==1)
    return list(merged.values())

def completed_titles(fixtures,formats,leagues,today,season,label):
    finals={};campaigns={}
    for m in fixtures:
        if m['date']<season:continue
        info=formats.get(m['stage'],{})
        kind=info.get('kind') or m.get('stageKind')
        edition=season_of(m['date'],season)
        if kind==10:finals.setdefault((edition,m['root'],m['stage'],m['asset']),[]).append(m)
        if m['asset'] in leagues:campaigns.setdefault((edition,m['root'],m['asset']),[]).append(m)
    result=[]
    def played(m):
        return m.get('played') and m['date']<=today and all(type(m.get(k)) is int and 0<=m[k]<100 for k in ('homeScore','awayScore'))
    def award(edition,root,asset,club,date):
        result.append(dict(competition=asset,root=root,club=club,date=date,season=edition,
                           year=date//10000,name=label(asset),origin='career'))
    for (edition,root,stage,asset),legs in finals.items():
        expected={'KO1LEG':1,'KO2LEGS':2}.get(formats.get(stage,{}).get('mode'))
        if not expected or len(legs)!=expected or not all(played(m) for m in legs):continue
        teams={m[t] for m in legs for t in ('home','away')}
        if len(teams)!=2:continue
        a,b=sorted(teams);scores={a:0,b:0}
        for m in legs:scores[m['home']]+=m['homeScore'];scores[m['away']]+=m['awayScore']
        if scores[a]==scores[b]:continue
        award(edition,root,asset,a if scores[a]>scores[b] else b,max(m['date'] for m in legs))
    for (edition,root,asset),matches in campaigns.items():
        members=set(leagues[asset]['members']);n=len(members)
        historical={m[t] for m in matches for t in ('home','away')}
        if edition<season_of(today,season) and len(historical)==n:members=historical
        if n<4 or not matches or not all(played(m) for m in matches):continue
        pairs={};table={t:[0,0,0] for t in members}
        for m in matches:
            h,a=m['home'],m['away']
            if h not in members or a not in members or h==a:break
            pair=tuple(sorted((h,a)));pairs[pair]=pairs.get(pair,0)+1;hg,ag=m['homeScore'],m['awayScore']
            for club,gf,ga in ((h,hg,ag),(a,ag,hg)):
                table[club][0]+=3 if gf>ga else 1 if gf==ga else 0;table[club][1]+=gf-ga;table[club][2]+=gf
        else:
            if len(pairs)!=n*(n-1)//2 or len(set(pairs.values()))!=1 or next(iter(pairs.values())) not in (1,2):continue
            ranked=sorted(table,key=lambda t:tuple(-v for v in table[t]))
            if table[ranked[0]]==table[ranked[1]]:continue
            award(edition,root,asset,ranked[0],max(m['date'] for m in matches))
    return result
