"""Prefer dated, contract-owned games when a complete campaign is retained."""
import json
from collections import defaultdict


def complete_campaigns(appointments, results, campaigns):
    clubs={a['id']:a['club_id'] for a in appointments}
    phases={}
    for row in campaigns:
        club=clubs.get(row['appointment'])
        if club is None:continue
        key=(club,row['game_date']//10000,row['root'],row['asset'],row['competition_key'])
        phases[key]=max(phases.get(key,0),sum(json.loads(row['counters'])[:6]))
    totals=defaultdict(int)
    for key,n in phases.items():totals[key[:4]]+=n
    dated=defaultdict(set)
    for r in results:
        for side in ('home','away'):
            dated[(r[side],r['game_date']//10000,r['root'],r['competition_id'])].add(r['match_key'])
    return {key for key,n in totals.items() if n and len(dated[key])>=n}


def without_complete(appointments, rows, complete):
    clubs={a['id']:a['club_id'] for a in appointments}
    initial={a['id'] for a in appointments if a['origin'] in ('Vínculo inicial desde o início da carreira','Estimado a partir da ativação do mod')}
    return [r for r in rows if r['appointment'] in initial or (clubs.get(r['appointment']),r.get('year',r['game_date']//10000),r['root'],r['asset']) not in complete]
