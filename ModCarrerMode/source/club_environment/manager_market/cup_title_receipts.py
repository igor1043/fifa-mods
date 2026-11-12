"""Durable cup finals and saved season outcomes, independent of current draw.

Older seasons can lose their fixture slots when FIFA creates the next draw.
An explicit saved final outcome plus two proven finalists can recover the
winner, without inventing a score, exact date or manager appointment.
"""
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from datetime import date,timedelta
import csv


@lru_cache(maxsize=2)
def _formats(game,stamp):
    from competition_formats import read_formats
    folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
    settings=defaultdict(dict);last=defaultdict(int)
    for r in csv.reader((folder/'settings.txt').read_text(encoding='utf-8-sig').splitlines()):
        if len(r)==3 and r[0].isdigit():settings[int(r[0])][r[1]]=r[2]
    for r in csv.reader((folder/'schedule.txt').read_text(encoding='utf-8-sig').splitlines()):
        if len(r)>=2 and r[0].isdigit() and r[1].isdigit():last[int(r[0])]=max(last[int(r[0])],int(r[1]))
    formats=read_formats(game)
    for stage,row in formats.items():
        row.update(asset=int(settings[row['root']].get('asset_id','0')),last_day=last[stage])
    return formats


def formats(game):
    folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
    try:
        stamp=tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in (folder/(n+'.txt') for n in ('compobj','settings','schedule')))
        return _formats(str(game),stamp)
    except (OSError,ValueError):return {}


def unique_matches(rows):
    found={};conflicts=set()
    for r in rows:
        m=dict(r);m.setdefault('asset',m.get('competition_id'));m.setdefault('date',m.get('game_date'))
        m.setdefault('homeScore',m.get('hg'));m.setdefault('awayScore',m.get('ag'));m.setdefault('played',True)
        if not m.get('played') or not all(type(m.get(k)) is int and 0<=m[k]<100 for k in ('homeScore','awayScore')):continue
        key=tuple(m[k] for k in ('root','asset','stage','date','home','away'))
        old=found.get(key)
        if old and (old['homeScore'],old['awayScore'])!=(m['homeScore'],m['awayScore']):conflicts.add(key)
        found[key]=m
    return [m for key,m in found.items() if key not in conflicts]


def winner(legs,mode):
    expected={'KO1LEG':1,'KO2LEGS':2}.get(mode)
    if not expected or len(legs)!=expected:return None
    teams={m[k] for m in legs for k in ('home','away')}
    if len(teams)!=2:return None
    scores={t:0 for t in teams}
    for m in legs:scores[m['home']]+=m['homeScore'];scores[m['away']]+=m['awayScore']
    ranked=sorted(scores,key=scores.get,reverse=True)
    return ranked[0] if scores[ranked[0]]>scores[ranked[1]] else None


def completed(rows,progress,definitions,today,first,label,performance=()):
    from title_evidence import completed_titles,season_of
    rows=[r for r in unique_matches(rows) if r['date']<=today]
    exact=[dict(t,asset=t['competition'],evidence_source='confirmed_cup_journal') for t in completed_titles(rows,definitions,{},today,first,label)]
    current=season_of(today,first);result=list(exact)
    counters=defaultdict(dict)
    for original in performance:
        r=dict(original);key=r.get('key',r.get('competition_key',''));parts=key.split(':')
        if len(parts)!=3 or parts[0]!='fce' or not all(v.isdigit() for v in parts[1:]):continue
        if r.get('source') not in ('fce','native_view','saved_fce'):continue
        season=int(r['season'])//100*100+1;club=r.get('club',r.get('club_id'));observed=r.get('date',r.get('game_date',0))
        values=tuple(r.get(k) for k in ('hw','hd','hl','aw','ad','al'))
        identity=(int(parts[1]),int(parts[2]),season)
        if any(type(v)!=int or v<0 for v in values) or sum(values)!=1:
            counters[identity].pop(club,None);continue
        counters[identity][club]=(values,observed)
    for m in rows:
        final=definitions.get(m['stage'],{});edition=season_of(m['date'],first)
        if final.get('kind')!=10 or final.get('mode')!='KO1LEG' or m['homeScore']!=m['awayScore']:continue
        groups=final.get('groups',[])
        if len(groups)!=1 or any(t['root']==m['root'] and t['season']==edition for t in result):continue
        evidence=counters.get((m['root'],groups[0],edition),{})
        if set(evidence)!={m['home'],m['away']} or any(not m['date']<=observed<=today for _,observed in evidence.values()):continue
        winners=[club for club,(v,_) in evidence.items() if v[0]+v[3]==1]
        losers=[club for club,(v,_) in evidence.items() if v[2]+v[5]==1]
        if len(winners)!=1 or len(losers)!=1 or winners[0]==losers[0]:continue
        # Native final W/L can prove a penalty winner while the retained
        # regulation score remains a draw. Keep that original score intact.
        result.append(dict(root=m['root'],asset=m['asset'],club=winners[0],season=edition,date=m['date'],name=label(m['asset']),evidence_source='confirmed_native_final'))
    for fact in progress:
        ordinal=fact.get('season');club=fact.get('teamid');root=fact.get('compobjid');stage=fact.get('stageid')
        if type(ordinal)!=int or ordinal<1 or type(club)!=int or club<=0 or fact.get('hasteamwon') not in (0,1):continue
        final=definitions.get(stage,{})
        if final.get('kind')!=10 or final.get('root')!=root or final.get('asset',0)<=0:continue
        asset=final['asset'];code=str(fact.get('compshortname',''))
        if code.startswith('C') and code[1:].isdigit() and int(code[1:])!=asset:continue
        year=first//10000+ordinal-1;season=year*10000+(first//100%100)*100+1
        if season>current or any(t['root']==root and t['season']==season for t in result):continue
        campaign=[r for r in rows if r['root']==root and r['asset']==asset and season_of(r['date'],first)==season]
        legs=[r for r in campaign if r['stage']==stage];expected={'KO1LEG':1,'KO2LEGS':2}.get(final.get('mode'))
        teams={r[k] for r in legs for k in ('home','away')}
        # Saved explicit winner/runner-up can resolve a played final decided
        # on penalties. A pending final with no result cannot grant a title.
        if expected and len(legs)==expected and len(teams)==2 and club in teams:
            won=club if fact['hasteamwon'] else next(t for t in teams if t!=club)
            result.append(dict(root=root,asset=asset,club=won,season=season,date=max(r['date'] for r in legs),name=label(asset),evidence_source='saved_final_outcome:exact'))
            continue
        # Recovery without a final score is only for a finished calendar-year
        # edition, after its scheduled final, with a completed native outcome.
        if season>=current or not 0<final.get('last_day',0)<=366 or fact.get('cup_objective_result',-1)<0:continue
        semis={s:f for s,f in definitions.items() if f.get('root')==root and f.get('kind')==8}
        if len(semis)!=1:continue
        semi,definition=next(iter(semis.items()));ties=defaultdict(list)
        for m in campaign:
            if m['stage']==semi:ties[tuple(sorted((m['home'],m['away'])))].append(m)
        finalists={winner(tie,definition.get('mode')) for tie in ties.values()}
        if len(ties)!=2 or len(finalists)!=2 or None in finalists or club not in finalists:continue
        won=club if fact['hasteamwon'] else next(t for t in finalists if t!=club)
        start=date(year,first//100%100,1);end=start.replace(year=year+1)-timedelta(days=1)
        last_semi=max(m['date'] for tie in ties.values() for m in tie)
        result.append(dict(root=root,asset=asset,club=won,season=season,date=end.year*10000+end.month*100+end.day,
            name=label(asset),evidence_source='saved_final_outcome:season',ownership_start=last_semi))
    return result


def receipts(market,context):
    game=market.catalog.parents[3] if len(market.catalog.parents)>3 else market.catalog.parent
    definitions=formats(game)
    if not definitions:return []
    stages=tuple(s for s,r in definitions.items() if r['kind'] in (8,10))
    if not stages:return []
    today=context['date'];first=context.get('title_start',context.get('career_start_date',context.get('season',today)))
    progress=context.get('title_progress',[])
    live=[m for m in context.get('title_fixtures',context.get('fixtures',[])) if m.get('stage') in stages and m.get('played') and m.get('date',0)<=today]
    final_keys=tuple(f'fce:{r["root"]}:{g}' for r in definitions.values() if r['kind']==10 for g in r.get('groups',[]))
    final_set=set(final_keys)
    performance=[r for r in context.get('performance',[]) if r.get('key') in final_set]
    signature=(market.branch,today//10000,str(progress),str(live),str(performance))
    cached=getattr(market,'_cup_title_receipts',None)
    if cached and cached[0]==signature:return cached[1]
    # Keep a bounded window, including first legs played before New Year.
    lower=max(first,(today//10000-2)*10000+101)
    history=market.rows('results','game_date>=? AND stage IN ('+','.join('?' for _ in stages)+')',(lower,*stages))
    archived=market.rows('performance_evidence','season>=? AND competition_key IN ('+','.join('?' for _ in final_keys)+')',(lower,*final_keys)) if final_keys else []
    from competition_labels import resolve
    result=completed([*history,*live],progress,definitions,today,first,lambda asset:resolve(game,asset,''),[*archived,*performance])
    market._cup_title_receipts=(signature,result)
    return result
