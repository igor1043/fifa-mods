"""Read-only, on-demand history for one club across all retained seasons."""
from pathlib import Path
from collections import defaultdict

def request(path,observed,model,now):
    fields=dict(line.split('=',1) for line in Path(path).read_text(encoding='ascii').splitlines() if '=' in line)
    saved,profile=observed['save'],observed['profile']
    if fields.get('schema')!='1':raise ValueError('Pedido incompatível')
    for key,value in dict(pid=saved['pid'],created=saved['process_created_100ns'],club=profile['club_id'],epoch=profile.get('context_epoch',0),date=observed['date']).items():
        if int(fields[key])!=value:raise ValueError('Histórico de outra sessão')
    if int(fields['context'],16)!=profile['context_address'] or not 0<=now-int(fields['captured_tick'])<=30000:raise ValueError('Pedido expirado')
    parts=fields['wire'].split('|')
    if len(parts)!=8 or parts[0]!='S16MGRH1' or parts[-1]!='END' or parts[1]!=model.get('profileToken'):raise ValueError('Catálogo substituído')
    values=[int(v) for v in parts[2:-1]]
    if any(v<0 or v>200000 for v in values):raise ValueError('Navegação inválida')
    club,country,league,page,focus=values
    if club not in ({r[2] for r in model['historyClubRows']} if 'historyClubRows' in model else {int(r[4].split('_')[1]) for r in model['clubRows']}):raise ValueError('Clube fora do catálogo')
    return dict(identity=(int(fields['captured_tick']),fields['wire']),club=club,resume=dict(tab=4,country=country,league=league,page=page,focus=540,clubTimeline=True,profile=False,timelinePage=0))

def build(market,club_id,people):
    from career_profile import build as career
    from model import stamp
    from evidence_ownership import complete_campaigns,without_complete
    club=market.one('clubs','club_id',club_id)
    if not club:raise ValueError('Clube não encontrado nesta carreira')
    appointments=market.rows('appointments','club_id=?',(club_id,))
    result=dict(club=club_id,name=club['name'],crest='crest_'+str(club_id),rows=[])
    if not appointments:return result
    ids={a['id'] for a in appointments};coaches={a['coach_id'] for a in appointments}
    people_index={p['id']:(i,p) for i,p in enumerate(people)}
    persons={p['coach_id']:p for p in market.rows('coaches','coach_id IN ('+','.join('?' for _ in coaches)+')',tuple(coaches))}
    results=market.rows('results','home=? OR away=?',(club_id,club_id));honours=market.rows('honours','club_id=?',(club_id,))
    moves=market.rows('movements','club_id=?',(club_id,));renewals={m['id'] for m in moves if m['kind']=='renewal'}
    for a in appointments:a['renewal']=a['id'] in renewals
    campaigns=market.rows('appointment_campaigns','appointment IN ('+','.join('?' for _ in ids)+')',tuple(ids))
    campaigns=without_complete(appointments,campaigns,complete_campaigns(appointments,results,campaigns))
    reviews={club_id:market.rows('reviews','club_id=?',(club_id,))}
    spells=[]
    for coach in sorted(coaches):
        if coach not in persons or coach not in people_index:continue
        index,person=people_index[coach]
        rich=career(persons[coach],appointments,results,honours,reviews,{club_id:club},market.info()['game_date'],stamp,campaigns,moves)
        for spell in rich['spells']:
            stats=spell['total']
            row=[person['name'],person['head'],spell['dates'],spell['duration'],spell['status'],str(stats['games']),str(stats['wins']),str(stats['draws']),str(stats['losses']),f"{stats['percentage']:.1f}%".replace('.',','),str(spell['titles']),index]
            spells.append((spell['start'],coach,row))
    result['rows']=[r for _,_,r in sorted(spells,key=lambda r:(-r[0],r[2][4]!='Atual',r[1]))]
    return result
