"""Round-by-round results, grouped by the native round and stage identity."""
from collections import defaultdict


def build_rounds(fixtures,today,league=True):
    grouped=defaultdict(list)
    for source in fixtures:
        try:
            number=int(source.get('round') or 0);home=int(source['home']);away=int(source['away'])
            date=int(source['date']);stage=int(source.get('stage') or 0);group=int(source.get('group') or 0)
        except (KeyError,TypeError,ValueError):continue
        if number<=0 or min(home,away)<=0 or home==away or not 20000101<=date<=22001231:continue
        row=dict(source)
        row['played']=bool(row.get('played') and date<=today and type(row.get('homeScore')) is int and type(row.get('awayScore')) is int and min(row['homeScore'],row['awayScore'])>=0)
        grouped[stage,group,number].append(row)
    result=[]
    for (stage,group,number),rows in grouped.items():
        unique={int(row['id']):row for row in rows};rows=sorted(unique.values(),key=lambda r:(r['date'],str(r.get('time','')),r['id']))
        result.append(dict(number=number,stage=stage,group=group,name=('Rodada ' if league else 'Jogos · rodada ')+str(number),
                           date=min(r['date'] for r in rows),played=sum(r['played'] for r in rows),matches=rows))
    # Reordered/postponed match dates must not turn next/previous round into
    # next/previous calendar day. Retain the competition engine's numbering.
    stage_start={stage:min(r['date'] for r in result if r['stage']==stage) for stage in {r['stage'] for r in result}}
    result.sort(key=(lambda r:(stage_start[r['stage']],r['stage'],r['group'],r['number'])) if league else (lambda r:(r['date'],r['stage'],r['group'],r['number'])))
    return result
