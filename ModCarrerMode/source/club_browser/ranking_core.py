"""Deterministic career rankings, independent of UI, memory access or save writes."""
from datetime import date,timedelta
from collections import defaultdict
import math

def day(value):
    value=int(value);return date(value//10000,value//100%100,value%100)

def seed(team,rules):
    r=rules[team['kind']];overall=max(1,min(99,team.get('overall') or 50));prestige=max(0,min(20,team.get('international') or 0))
    return max(100.,r['seed_base']+(overall-r.get('overall_origin',0))*r['overall_weight']+prestige*r['prestige_weight']+max(0,min(20,team.get('domestic') or 0))*r.get('domestic_prestige_weight',0))

def expectation(a,b,divisor=600):return 1/(1+10**max(-12,min(12,(b-a)/divisor)))

def importance(meta,national,knockout,rules):
    kind=meta.get('type','');scope=meta.get('scope','domestic')
    if national:
        r=rules['nations']
        if kind=='INTERQUAL':return r['qualifier']
        if kind not in ('CUP','INTERCUP','LEAGUE'):return r['friendly']
        return r[('world' if scope=='world' else 'continental')+('_knockout' if knockout else '_group')]
    r=rules['clubs'];key='world' if scope=='world' else 'continental' if scope=='continental' else 'league' if kind=='LEAGUE' else 'supercup' if kind=='SUPERCUP' else 'cup' if kind in ('CUP','PLAYOFF') else 'friendly'
    # Strength is derived from the installed participants, not a country whitelist.
    strength=max(.6,min(1.4,(meta.get('strength') or 65)/70))
    return r[key]*strength*(1.15 if knockout and kind!='SUPERCUP' else 1)

def canonical_matches(matches,teams,today):
    """One completed fixture per identity. Future/unfinished/cross-kind games ignored."""
    latest={}
    for m in matches:
        try:
            key=(int(m['date']),int(m['root']),int(m['id']))
            a,b=teams.get(m['home']),teams.get(m['away'])
            if not a or not b or a['id']==b['id'] or a['kind']!=b['kind'] or not m['played'] or day(key[0])>day(today):continue
            if any(type(m.get(k)) is not int or not 0<=m[k]<100 for k in ('homeScore','awayScore')):continue
            if key in latest and any(latest[key][k]!=m[k] for k in ('home','away','homeScore','awayScore')):raise ValueError('Resultados divergentes para a mesma partida.')
            latest[key]=m
        except (KeyError,TypeError,OverflowError):continue
    return sorted(latest.values(),key=lambda m:(m['date'],m['root'],m['id']))

def confirmed_titles(schedule,teams,meta,today,formats):
    groups=defaultdict(list)
    for m in schedule:
        if m.get('home') in teams and m.get('away') in teams:
            # European seasons cross January. Never award a partial calendar
            # half as a league title; require the whole root's round robin.
            root=m.get('root');year=0 if meta.get(root,{}).get('type')=='LEAGUE' else m['date']//10000
            groups[(root,year)].append(m)
    awards=[]
    for (root,year),all_games in groups.items():
        finals=[m for m in all_games if m.get('stageKind')==10]
        league=meta.get(root,{}).get('type')=='LEAGUE'
        candidates=finals if finals else all_games if league else []
        # Dates alone never imply completion. No bonus after only a first leg.
        if not candidates or any(not m.get('played') or m['date']>today or m.get('homeScore') is None or m.get('awayScore') is None for m in candidates):continue
        if finals:
            pairs={tuple(sorted((m['home'],m['away']))) for m in finals}
            if len(pairs)!=1:continue
            a,b=next(iter(pairs));expected=2 if any(formats.get(m.get('stage'),{}).get('mode')=='KO2LEGS' for m in finals) else 1
            if len(finals)!=expected:continue
            h=sum(m['homeScore'] if m['home']==a else m['awayScore'] for m in finals);v=sum(m['awayScore'] if m['home']==a else m['homeScore'] for m in finals)
            winner=a if h>v else b if v>h else None  # PSO winner unavailable: never guess.
        else:
            table=defaultdict(lambda:[0,0,0,0]);meetings=defaultdict(int)
            for m in candidates:
                a,b=m['home'],m['away'];h,v=m['homeScore'],m['awayScore'];meetings[tuple(sorted((a,b)))]+=1
                for team,gf,ga in ((a,h,v),(b,v,h)):
                    table[team][0]+=3 if gf>ga else 1 if gf==ga else 0;table[team][1]+=int(gf>ga);table[team][2]+=gf-ga;table[team][3]+=gf
            n=len(table)
            # A partial/one-team or incomplete round robin cannot award a title.
            if n<3 or len(meetings)!=n*(n-1)//2 or len(set(meetings.values()))!=1:continue
            order=sorted(table,key=lambda t:table[t],reverse=True)
            # Different associations have different tiebreakers; tied points do not prove a champion.
            winner=order[0] if table[order[0]][0]>table[order[1]][0] else None
        if winner:
            at=max(m['date'] for m in candidates)
            awards.append(dict(root=root,year=at//10000,team=winner,date=at))
    return awards

def calculate(catalog,schedule,metadata,today,rules,titles=()):
    teams={r['id']:dict(r) for r in catalog};today_date=day(today);cutoff=today_date.replace(year=today_date.year-rules['years']) if not (today_date.month==2 and today_date.day==29) else date(today_date.year-rules['years'],2,28)
    games=[m for m in canonical_matches(schedule,teams,today) if day(m['date'])>=cutoff]
    rows={key:dict(t,points=seed(t,rules),initial=seed(t,rules),matchPoints=0.,titlePoints=0.,games=0,wins=0,draws=0,losses=0,titles=0,form=[],recent=[]) for key,t in teams.items()}
    def ordered():return {kind:sorted([r for r in rows.values() if r['kind']==kind],key=lambda r:(-round(r['points'],6),-r['wins'],r['name'].casefold(),r['id'])) for kind in ('clubs','nations')}
    previous=None;last_date=max([m['date'] for m in games]+[a['date'] for a in titles if a.get('date',today+1)<=today],default=0)
    awards=defaultdict(list)
    for a in titles:
        if a.get('team') in rows and cutoff<=day(a['date'])<=today_date:awards[a['date']].append(a)
    days=defaultdict(list)
    for m in games:days[m['date']].append(m)
    for at in sorted(set(days)|set(awards)):
        if at==last_date:previous={r['id']:i+1 for group in ordered().values() for i,r in enumerate(group)}
        for m in days[at]:
            a,b=rows[m['home']],rows[m['away']];h,v=m['homeScore'],m['awayScore'];national=a['kind']=='nations';knockout=m.get('stageKind',0)>2;meta=metadata.get(m['root'],{})
            weight=importance(meta,national,knockout,rules);k=weight if national else rules['clubs']['match_k']*weight
            w=1. if h>v else .5 if h==v else 0.;e=expectation(a['points'],b['points'],rules[a['kind']]['elo_divisor']);delta_a=k*(w-e);delta_b=k*((1-w)-(1-e))
            if national and knockout and meta.get('type')!='INTERQUAL':delta_a=max(0.,delta_a);delta_b=max(0.,delta_b)
            for row,delta,gf,ga,opponent in ((a,delta_a,h,v,b),(b,delta_b,v,h,a)):
                row['points']+=delta;row['matchPoints']+=delta;row['games']+=1;result='V' if gf>ga else 'E' if gf==ga else 'D';row['wins']+=result=='V';row['draws']+=result=='E';row['losses']+=result=='D';row['form']=(row['form']+[result])[-5:]
                row['recent']=(row['recent']+[dict(date=at,opponent=opponent['name'],score=f'{gf}–{ga}',delta=round(delta,2),importance=round(weight,2))])[-5:]
        for award in awards[at]:
            r=rows[award['team']];r['titles']+=1
            if r['kind']=='clubs':
                bonus=rules['clubs']['title_bonus']*importance(metadata.get(award['root'],{}),False,False,rules)*rules['clubs']['title_year_decay']**max(0,today_date.year-award['year'])
                r['points']+=bonus;r['titlePoints']+=bonus
    result=ordered()
    for group in result.values():
        for position,r in enumerate(group,1):
            r['rank']=position;r['movement']=previous.get(r['id'],position)-position if previous else 0
            for key in ('points','initial','matchPoints','titlePoints'):r[key]=round(r[key],2)
    return dict(schema=1,date=today,groups=result,matches=len(games),referenceDate=last_date)

def reconcile(result,schedule,evidence,metadata,rules):
    """Include aggregate-only games once, without fictional Elo opponents.

    Elo remains restricted to actual fixtures. Missing W/D/L contributes a
    separate, disclosed campaign component. A conflicting aggregate is not
    subtracted from unrelated or historical fixtures.
    """
    rows={r['id']:r for g in result['groups'].values() for r in g};detailed=defaultdict(lambda:[0,0,0])
    for m in canonical_matches(schedule,rows,result['date']):
        if m['date']<evidence.get('seasonStart',0):continue
        for t,gf,ga in ((m['home'],m['homeScore'],m['awayScore']),(m['away'],m['awayScore'],m['homeScore'])):
            detailed[(m['asset'],t)][0 if gf>ga else 1 if gf==ga else 2]+=1
    roots={r['asset']:r['root'] for r in evidence.get('performance',[]) if r['root']>0}
    for r in rows.values():r.update(campaignPoints=0.,campaignGames=0,percentage=round(100*(3*r['wins']+r['draws'])/(3*r['games']),2) if r['games'] else 0,competitionPoints=3*r['wins']+r['draws'])
    for summary in evidence['summaries']:
        r=rows.get(summary['club'])
        if r is None:continue
        known=detailed[(summary['asset'],r['id'])];total=[summary[k] for k in ('wins','draws','losses')];missing=[a-b for a,b in zip(total,known)]
        # Standings can classify a penalty tie as W/L while its retained score
        # is a draw. Use the authoritative campaign counters for display, and
        # retain the actual score for Elo. Never invent a penalty result.
        if sum(missing)<0:continue
        w,d,l=missing;count=w+d+l
        r['games']+=count;r['wins']+=w;r['draws']+=d;r['losses']+=l
        if not count:continue
        info=metadata.get(roots.get(summary['asset']),dict(type='LEAGUE',scope='domestic',strength=r.get('overall',65)))
        factor=importance(info,r['kind']=='nations',False,rules)
        if r['kind']=='nations':factor/=25.
        # A mean campaign yields little change; strong/weak campaigns add/lose
        # points. Normalize long calendars without creating fake match rows.
        bonus=rules.get('campaign_scale',2.)*factor*(3*w+d-1.25*count)*min(1.,38/count)
        r['campaignPoints']+=bonus;r['campaignGames']+=count;r['points']+=bonus;r['matchPoints']+=bonus
    changed=any(r['campaignGames'] for r in rows.values())
    for group in result['groups'].values():
        group.sort(key=lambda r:(-round(r['points'],6),-r['wins'],r['name'].casefold(),r['id']))
        for i,r in enumerate(group,1):
            r['rank']=i;r['competitionPoints']=3*r['wins']+r['draws'];r['percentage']=round(r['competitionPoints']*100/(3*r['games']),2) if r['games'] else 0
            for key in ('campaignPoints','points','matchPoints'):r[key]=round(r[key],2)
            if changed:r['movement']=0  # Summaries do not provide a previous match date/rank.
    result['coverage']=evidence['coverage'];result['aggregateTeamAppearances']=sum(r['campaignGames'] for r in rows.values())
    return result
