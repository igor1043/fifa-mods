"""Lightweight 2D publication. It shares confirmed honours with the 3D room."""
import hashlib,json
from pathlib import Path
from . import assets,data

CAPACITY=18


def records(game,req,cups,rows):
    result=[]
    for source in rows:
        row=dict(source);club=int(row.get('club',req['club']));winner,_=assets.club_identity(game,club)
        trophy=data.trophy_identity(row['competition'],cups)
        wins=[]
        for victory in row.get('wins',[row]):
            winning_club=int(victory.get('club',req['club']));name=assets.club_identity(game,winning_club)[0]['name']
            wins.append(dict(year=victory['year'],date=victory['date'],club=winning_club,club_name=name))
        result.append(dict(row,club=club,club_name=winner['name'],trophy=trophy,wins=wins,
            title_count=len(wins),first_year=min(w['year'] for w in wins),last_year=max(w['year'] for w in wins),thumbnail=assets.trophy_thumbnail(game,trophy)))
    return result


def serialize(magic,pid,req,generation,total,page,pages,rows):
    quote=lambda s:json.dumps(str(s),ensure_ascii=False)
    lines=[f'{magic} 2 {pid} {req["club"]} {req["epoch"]} {int(req.get("collection")=="coach")} {generation} {total} {page} {pages} {len(rows)}']
    for row in rows:
        lines.append(' '.join(str(int(row[k])) for k in ('trophy','competition','club','date','year','title_count','first_year','last_year'))+' '+
            ' '.join(quote(row[k]) for k in ('name','club_name','origin','thumbnail')))
        for win in row['wins']:lines.append(f'{win["year"]} {win["club"]} {win["date"]} '+quote(win['club_name']))
    return ('\n'.join(lines)+'\n').encode('utf8')


def publish(game,pid,req,snapshot,identity,cups,all_rows,branch):
    game=Path(game);folder=game/'ModCarrerMode/runtime/trophy_room'
    rows,page,pages=data.page_rows(all_rows,req.get('shelf_page',0),CAPACITY)
    page_records=records(game,req,cups,rows)
    signature=hashlib.sha256(json.dumps(['cabinet-v2',pid,req['club'],req['epoch'],req.get('collection','club'),branch,page_records,page,len(all_rows)],sort_keys=True).encode()).hexdigest()[:16]
    generation=int(signature[:7],16)
    from .worker import scoped_request
    current=scoped_request(game,pid)
    if not current or any(current.get(k)!=req.get(k) for k in ('pid','club','epoch','presentation','shelf_page','collection')):
        raise InterruptedError('O acervo ou a carreira mudou durante a leitura')
    live=json.loads((game/'ModCarrerMode/runtime/career_fce_snapshot.json').read_bytes())
    if any(live.get(k)!=snapshot.get(k) for k in ('pid','club','fceContextEpoch','date','savePath')):
        raise InterruptedError('A carreira mudou durante a leitura dos títulos')
    assets.atomic(folder/'cabinet.tsv',serialize('S16CABINET',pid,req,generation,len(all_rows),page,pages,page_records))
    assets.atomic(folder/'cabinet.json',json.dumps(dict(schema=1,signature=signature,pid=pid,club=req['club'],epoch=req['epoch'],
        collection=req.get('collection','club'),generation=generation,total=len(all_rows),page=page,pages=pages,rows=page_records,save=snapshot['savePath'],date=snapshot['date']),ensure_ascii=False,indent=2).encode('utf8'))
    return signature
