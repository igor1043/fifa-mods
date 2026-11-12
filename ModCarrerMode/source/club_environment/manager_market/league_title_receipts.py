"""Compact honours from completed native league tables, including old seasons.

Only a standalone, single-group league with its full scheduled round count is
eligible. Group leaders, partial tables, playoffs and tied points are excluded.
No fixture, final score or historical award day is synthesized.
"""
from collections import defaultdict
from datetime import date,timedelta
from functools import lru_cache
from pathlib import Path
import csv


@lru_cache(maxsize=2)
def _definitions(folder,stamp):
    folder=Path(folder)
    def rows(name):return csv.reader((folder/(name+'.txt')).read_text(encoding='utf-8-sig').splitlines())
    objects={int(r[0]):r for r in rows('compobj') if len(r)>=5 and r[0].isdigit()}
    settings=defaultdict(dict)
    for r in rows('settings'):
        if len(r)==3 and r[0].isdigit():settings[int(r[0])][r[1]]=r[2]
    stages=defaultdict(list);teams=defaultdict(set);slots=defaultdict(set);rounds=defaultdict(set);last=defaultdict(int)
    for ident,r in objects.items():
        if r[1]=='4':stages[int(r[4])].append(ident)
    for r in rows('initteams'):
        if len(r)==3 and all(v.isdigit() for v in r):teams[int(r[0])].add(int(r[2]))
    for r in rows('standings'):
        if len(r)==2 and all(v.isdigit() for v in r):slots[int(r[0])].add(int(r[1]))
    for r in rows('schedule'):
        if len(r)>=3 and all(v.isdigit() for v in r[:3]):
            stage=int(r[0]);rounds[stage].add(int(r[2]));last[stage]=max(last[stage],int(r[1]))
    result={}
    for root,children in stages.items():
        opts=settings[root]
        if opts.get('comp_type')!='LEAGUE' or len(children)!=1:continue
        stage=children[0];groups=[i for i,r in objects.items() if r[1]=='5' and int(r[4])==stage]
        if settings[stage].get('match_stagetype')!='LEAGUE' or len(groups)!=1:continue
        n=len(slots[groups[0]] or teams[root] or teams[groups[0]])
        if n<4 or not rounds[stage]:continue
        round_count=len(rounds[stage]);base=n if n%2 else n-1
        if round_count%base or round_count//base not in (1,2):continue
        asset=opts.get('asset_id','')
        if not asset.isdigit() or int(asset)<=0:continue
        result[int(asset)]=dict(root=root,teams=n,games=(round_count//base)*(n-1),last_day=last[stage])
    return result


def definitions(game):
    folder=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata'
    try:
        stamp=tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in (folder/(n+'.txt') for n in ('compobj','settings','schedule','initteams','standings')))
        return _definitions(str(folder),stamp)
    except (OSError,ValueError):return {}


def completed(rows,definitions,today):
    groups=defaultdict(dict)
    for original in rows:
        row=dict(original);key=row.get('key',row.get('competition_key',''))
        if not key.startswith('db:') or '#cycle:' in key:continue
        try:
            asset=int(key.split(':')[1]);season=int(row['season']);club=int(row.get('club',row.get('club_id',0)))
            values=tuple(row[k] for k in ('hw','hd','hl','aw','ad','al'))
            if asset not in definitions or any(type(v)!=int or v<0 for v in values):continue
            season=season//10000*10000+max(1,min(12,season//100%100))*100+1
            group=groups[(season,asset)];old=group.get(club)
            if old is None or sum(values)>sum(old['values']):group[club]=dict(values=values,observed=row.get('date',row.get('game_date',today)))
        except (KeyError,TypeError,ValueError):continue
    result=[]
    for (season,asset),clubs in groups.items():
        definition=definitions[asset];n=definition['teams'];games=definition['games']
        if len(clubs)!=n or any(sum(row['values'])!=games for row in clubs.values()):continue
        # FIFA's secondary-league simulations publish per-club W/D/L, not a
        # paired fixture ledger. Their totals need not balance across clubs;
        # the native completed table remains the authority for its ranking.
        start=date(season//10000,season//100%100,1);end=start.replace(year=start.year+1)-timedelta(days=1)
        observed=max(row['observed'] for row in clubs.values())
        scheduled=start+timedelta(days=max(0,definition['last_day']-1))
        observed_day=date(observed//10000,observed//100%100,observed%100)
        # Compare when this table was actually observed, not today's date.
        # A stale table sampled in January must never win a December season.
        if observed>today or observed_day.year*12+observed_day.month<scheduled.year*12+scheduled.month:continue
        points={club:3*(row['values'][0]+row['values'][3])+row['values'][1]+row['values'][4] for club,row in clubs.items()}
        ranked=sorted(points,key=lambda c:points[c],reverse=True)
        if points[ranked[0]]==points[ranked[1]]:continue
        historical=observed>end.year*10000+end.month*100+end.day
        award=end.year*10000+end.month*100+end.day if historical else min(observed,today)
        result.append(dict(asset=asset,root=definition['root'],club=ranked[0],season=season,date=award,
            evidence_source='completed_native_table:season' if historical else 'completed_native_table:observed',
            ownership_start=season if historical else award))
    return result


def receipts(market,context):
    game=market.catalog.parents[3] if len(market.catalog.parents)>3 else market.catalog.parent
    definitions_by_asset=definitions(game)
    if not definitions_by_asset:return []
    today=context['date'];rows=list(context.get('performance',[]))
    # One bounded recovery on first use; repeat around rollover when FIFA can
    # publish the just-finished table a few days after resetting the calendar.
    key=(market.branch,today//10000,today if today%10000<=107 else 0)
    if getattr(market,'_league_title_recovery',None)!=key:
        lower=(today//10000-1)*10000+101
        rows+=market.rows('performance_evidence','season>=? AND competition_key LIKE ?', (lower,'db:%'))
        market._league_title_recovery=key
    result=completed(rows,definitions_by_asset,today)
    if not result:return []
    from competition_labels import resolve
    for row in result:row['name']=resolve(game,row['asset'],'')
    return [row for row in result if row['name']]
