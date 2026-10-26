import portable_paths as portable
"""Read-only carousel information from the validated career snapshot and DB."""
from datetime import datetime
from pathlib import Path
import re


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


def stadium_settings(game):
    """Read only the installed venue mappings, without creating an INI file."""
    if game is None:return {}
    try:raw=(Path(game)/'FSW/settings.ini').read_bytes()
    except FileNotFoundError:return {}
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):text=raw.decode('utf16')
    else:
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:text=raw.decode('cp1252')
    sections={};section=''
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith((';','#')):continue
        if line.startswith('[') and line.endswith(']'):section=line[1:-1].strip().casefold()
        elif section in ('comp','stadium','scoreboardstdname') and '=' in line:
            key,value=line.split('=',1);sections.setdefault(section,{})[key.strip().casefold()]=value.strip()
    return sections


def stadium_display_name(key,settings):
    """Match the native next-match card: preserve aliases, omit city/country."""
    names=settings.get('scoreboardstdname',{});key=key.strip();lookup=key
    value=names.get(lookup.casefold(),'')
    # Legacy pools sometimes append numeric parameters without a comma.
    while not value and lookup and lookup[-1] in '0123456789':
        lookup=lookup[:-1];value=names.get(lookup.casefold(),'')
    if not value:return clean(key)
    value=clean(value.split(',',1)[0]).strip()
    separators=list(re.finditer(r' (?:-|–|—) ',value))
    if len(separators)>=2:value=value[:separators[-2].start()]
    return value.strip() or clean(key)


def stadium_title(home,league,rows,base,model_name,game=None):
    """FSW fixture override, then club-specific DB name, then the model label.

    The model ID is shared by many clubs; its label cannot identify the host's
    custom stadium. A saved assignment also takes precedence over the base DB.
    """
    settings=stadium_settings(game)
    pool=settings.get('comp',{}).get(str(league),'') if league>0 else ''
    names=[]
    for token in pool.split(','):
        token=token.strip()
        if not token or all(c in '0123456789' for c in token):break
        names.append(stadium_display_name(token,settings))
    if names:
        title=names[0] if len(names)==1 else names[0]+' - '+names[1]+(' + outras opcoes' if len(names)>2 else '')
        return title,'FSW/settings.ini [comp]'
    mapping=settings.get('stadium',{}).get(str(home),'').split(',',1)[0].strip()
    if mapping:return stadium_display_name(mapping,settings),'FSW/settings.ini [stadium]'
    assigned=[r for r in rows('stadiumassignments') if r.value('teamid')==home]
    source='stadiumassignments.stadiumcustomname (carreira / DB)'
    if not assigned:
        assigned=[r for r in base.get('stadiumassignments',[]) if r.value('teamid')==home]
        source='stadiumassignments.stadiumcustomname (DB base)'
    custom={clean(r.value('stadiumcustomname')).strip() for r in assigned}
    if len(custom)==1 and next(iter(custom)):return next(iter(custom)),source
    return model_name or 'Não informado','stadiums.name (modelo; sem nome personalizado)'


def stadium_location(home,league,game=None):
    settings=stadium_settings(game)
    pool=settings.get('comp',{}).get(str(league),'') if league>0 else ''
    venues=[]
    for token in pool.split(','):
        token=token.strip()
        if not token or all(c in '0123456789' for c in token):break
        venues.append(token)
    # A pool is selected when entering the match. Do not guess its city.
    if len(venues)>1:return ''
    key=venues[0] if venues else settings.get('stadium',{}).get(str(home),'').split(',',1)[0].strip()
    names=settings.get('scoreboardstdname',{});value=names.get(key.casefold(),'')
    while not value and key and key[-1] in '0123456789':
        key=key[:-1];value=names.get(key.casefold(),'')
    parts=re.split(r' (?:-|–|—) ',clean(value.split(',',1)[0]))
    return ', '.join(parts[-2:]).strip() if len(parts)>=3 else ''


def head_to_head(fixtures,user,opponent,today):
    """Count only resolved meetings available in this career snapshot."""
    games={r[0]:r for r in fixtures if len(r)>=10 and user>0 and opponent>0
           and user!=opponent and set(r[5:7])=={user,opponent}
           and r[9]==1 and r[3]<=today and 0<=r[7]<100 and 0<=r[8]<100}
    wins=draws=losses=0
    for r in games.values():
        gf,ga=(r[7],r[8]) if r[5]==user else (r[8],r[7])
        wins+=gf>ga;draws+=gf==ga;losses+=gf<ga
    return dict(user_wins=wins,draws=draws,opponent_wins=losses,games=len(games))


def enrich(payload,snapshot,rows,base,game=None):
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
        for player in team['players']:player['name']=clean(player['name']).strip()
    f=payload['fixture'];home=f[5];links=[r.value('stadiumid') for r in rows('teamstadiumlinks') if r.value('teamid')==home]
    # Ambiguous assignments must not silently display a different venue.
    stadium_id=links[0] if len(set(links))==1 else 0
    stadium=next((r for r in rows('stadiums') if r.value('stadiumid')==stadium_id),None)
    stadium_name=clean(stadium.value('name')) if stadium is not None else ''
    capacity=stadium.value('capacity') if stadium is not None else 0
    league=fixture_competition(f,nodes)
    league_name=competition_label(league) if league else ''
    stadium_name,venue_source=stadium_title(home,league,rows,base,stadium_name,game)
    payload['details']={'date':format_date(f[3]),'time':f'{f[4]//100:02d}:{f[4]%100:02d}',
                        'home_id':home,'home_name':names.get(home,''),'away_name':names.get(f[6],''),
                        'competition_id':league,'competition':league_name or ('Competição '+str(league) if league else 'Calendário da carreira'),
                        'stadium_id':stadium_id,'stadium':stadium_name or 'Não informado',
                        'location':stadium_location(home,league,game),
                        'capacity':f'{capacity:,}'.replace(',','.') if capacity>0 else 'Não informada',
                        'venue_source':venue_source,
                        'history_source':'Resultados concluídos desta carreira; do mais recente ao mais antigo.'}
    payload['head_to_head']=head_to_head(snapshot['fixtures'],payload['user']['team_id'],payload['opponent']['team_id'],payload['date'])
    return payload
