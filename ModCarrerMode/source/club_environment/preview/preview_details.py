import portable_paths as portable
"""Read-only carousel information from the validated career snapshot and DB."""
from datetime import datetime


def clean(text):
    text=str(text or '')
    for _ in range(3):
        if '\u00c3' not in text and '\u00c2' not in text:break
        try:text=text.encode('cp1252').decode('utf8')
        except UnicodeError:break
    return text


def contrast(rgb):
    # WCAG relative luminance: choose the higher-contrast neutral text.
    linear=[v/3294.6 if v<=10 else ((v/255+.055)/1.055)**2.4 for v in rgb]
    luminance=sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))
    return 0x182830 if (luminance+.05)/.05 >= 1.05/(luminance+.05) else 0xffffff


def primary(row,base=None):
    def value(key,default):
        for candidate in (row,base):
            if candidate is not None and key in candidate.fields:return max(0,min(255,int(candidate.value(key))))
        return default
    return tuple(value('teamcolor1'+c,d) for c,d in zip('rgb',(22,62,98)))


def format_date(date):
    try:return datetime.strptime(str(date),'%Y%m%d').strftime('%d/%m/%Y')
    except ValueError:return 'Não informada'


def fixture_competition(fixture,nodes):
    """Resolve this fixture's parent chain; a node ID is not a league ID."""
    node=fixture[1];seen=set()
    for _ in range(32):
        if node in seen:break
        seen.add(node);row=nodes.get(node)
        if row is None or len(row)<4:break
        if row[2]==3 and row[3]>0:return row[3]
        node=row[1]
    return 0


def recent(fixtures,team,today,names,limit=5,nodes=None,competition_label=None):
    completed={r[0]:r for r in fixtures if len(r)>=10 and team in r[5:7]
               and r[9]==1 and 0<=r[7]<100 and 0<=r[8]<100 and r[3]<=today}
    result=[]
    for r in sorted(completed.values(),key=lambda r:(r[3],r[4],r[0]),reverse=True)[:limit]:
        home=r[5]==team;opponent=r[6] if home else r[5]
        gf,ga=(r[7],r[8]) if home else (r[8],r[7])
        competition=fixture_competition(r,nodes or {})
        result.append({'fixture':r[0],'date':r[3],'date_text':format_date(r[3]),'opponent_id':opponent,
                       'opponent':names.get(opponent,'Clube '+str(opponent)),
                       'venue':'Casa' if home else 'Fora','goals_for':gf,'goals_against':ga,
                       'score':f'{gf} – {ga}','result':'V' if gf>ga else 'D' if gf<ga else 'E',
                       'competition_id':competition,
                       'competition':clean(competition_label(competition)) if competition and competition_label else 'Competição não informada'})
    return result


def enrich(payload,snapshot,rows,base):
    teams={r.value('teamid'):r for r in rows('teams')}
    original={r.value('teamid'):r for r in base.get('teams',[])}
    names={k:clean(v.value('teamname')) for k,v in teams.items()}
    nodes={r[0]:r for r in snapshot.get('nodes',[])}
    from competition_names_r57 import competition_name
    competition_cache={}
    def competition_label(ident):
        if ident not in competition_cache:competition_cache[ident]=clean(competition_name(ident,rows)) or 'Competição não informada'
        return competition_cache[ident]
    for side in ('user','opponent'):
        team=payload[side];ident=team['team_id'];rgb=primary(teams.get(ident),original.get(ident))
        team.update(name=clean(team['name']),primary=list(rgb),header_color=0xff000000|rgb[0]<<16|rgb[1]<<8|rgb[2],header_ink=contrast(rgb))
        team['recent']=recent(snapshot['fixtures'],ident,payload['date'],names,nodes=nodes,competition_label=competition_label)
        for player in team['players']:player['name']=clean(player['name'])
    f=payload['fixture'];home=f[5];links=[r.value('stadiumid') for r in rows('teamstadiumlinks') if r.value('teamid')==home]
    # Ambiguous assignments must not silently display a different venue.
    stadium_id=links[0] if len(set(links))==1 else 0
    stadium=next((r for r in rows('stadiums') if r.value('stadiumid')==stadium_id),None)
    stadium_name=clean(stadium.value('name')) if stadium is not None else ''
    capacity=stadium.value('capacity') if stadium is not None else 0
    league=fixture_competition(f,nodes)
    league_name=competition_label(league) if league else ''
    payload['details']={'date':format_date(f[3]),'time':f'{f[4]//100:02d}:{f[4]%100:02d}',
                        'home_id':home,'home_name':names.get(home,''),'away_name':names.get(f[6],''),
                        'competition_id':league,'competition':league_name or ('Competição '+str(league) if league else 'Calendário da carreira'),
                        'stadium_id':stadium_id,'stadium':stadium_name or 'Não informado',
                        'capacity':f'{capacity:,}'.replace(',','.') if capacity>0 else 'Não informada',
                        'venue_source':'Estádio vinculado ao mandante no save / banco do jogo',
                        'history_source':'Resultados concluídos desta carreira; do mais recente ao mais antigo.'}
    return payload
