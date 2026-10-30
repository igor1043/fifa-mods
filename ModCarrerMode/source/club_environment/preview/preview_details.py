import portable_paths as portable
"""Read-only carousel information from the validated career snapshot and DB."""
from datetime import datetime
from pathlib import Path
import re,sqlite3,sys,csv,json


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


def club_stadium_fallback(team_id,game):
    """Read the same club stadium row used by the native Central card."""
    if game is None or team_id<=0:return {}
    path=Path(game)/'ModCarrerMode/data/catalogs/club_stadium_fallback.tsv'
    try:raw=path.read_bytes()
    except OSError:return {}
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:text=raw.decode('cp1252',errors='replace')
    for line in text.splitlines():
        fields=line.rstrip('\r\n').split('|')
        if len(fields)<5:continue
        try:ident=int(fields[0].strip())
        except ValueError:continue
        if ident!=team_id:continue
        try:capacity=max(0,int(fields[2].strip()))
        except ValueError:capacity=0
        try:stadium_id=max(0,int(fields[1].strip()))
        except ValueError:stadium_id=0
        return {'team_id':ident,'stadium_id':stadium_id,
                'capacity':capacity,'name':clean(fields[3]).strip(),
                'image_key':clean(fields[4]).strip() or (str(stadium_id) if stadium_id else '')}
    return {}


def crowd_runtime_percent(game,club,opponent,fixture_date):
    """Mirror the percent shown by the Central card from its live bridge config."""
    if game is None:return None
    root=Path(game)/'ModCarrerMode'
    paths=(root/'config/crowd.ini',root/'crowd.ini')
    sections={};section='';found=False
    for path in paths:
        try:raw=path.read_bytes()
        except OSError:continue
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:text=raw.decode('cp1252',errors='replace')
        sections={};section=''
        for line in text.splitlines():
            line=line.strip()
            if not line or line.startswith((';','#')):continue
            if line.startswith('[') and line.endswith(']'):
                section=line[1:-1].strip().casefold();continue
            if section=='crowd' and '=' in line:
                key,value=line.split('=',1);sections[key.strip().casefold()]=value.split(';',1)[0].strip()
        if sections:found=True;break
    if not found:return None
    try:automatic=int(sections.get('automatic_dynamic_controller','1'))!=0
    except ValueError:automatic=True
    try:static_percent=int(sections.get('static_factor_percent','-1'))
    except ValueError:static_percent=-1
    if not automatic and 0<=static_percent<=90:
        return static_percent
    # In automatic mode the native controller publishes its current rounded
    # decision into this exact setting before the Central card reads it.
    if 0<=static_percent<=90:return static_percent
    # If the config is in fallback mode, use the native bridge record only
    # when it belongs to this club, opponent, and fixture date.
    log=root/'logs/crowd_attendance_runtime.log'
    try:lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
    except OSError:return None
    expected={'club':str(club),'opponent':str(opponent),'date':str(fixture_date)}
    for line in reversed(lines):
        if not line.startswith('dynamic_factor_bridge '):continue
        values=dict(re.findall(r'([a-z_]+)=([^\s]+)',line))
        if any(values.get(key)!=value for key,value in expected.items()):continue
        try:percent=int(values.get('percent','0'))
        except ValueError:continue
        if 1<=percent<=100:return percent
    return None


def finance_gate(save,save_hash,club,season,competition,home,neutral,capacity,prestige,match_date=0,*,occupancy_percent=None):
    """Read the active finance policy without creating or changing its ledger."""
    bank_dir=Path(__file__).resolve().parents[1]/'bank'
    if str(bank_dir) not in sys.path:sys.path.insert(0,str(bank_dir))
    from club_finance import DEFAULT_RULES,ticket_projection,match_terms
    club_profile=None
    policy=dict(DEFAULT_RULES);settings={'enabled':True,'tickets':True};sidecar=Path(str(Path(save).parent/'server16_loans.sqlite3').removeprefix('\\\\?\\')) if save else None
    if save_hash and sidecar is not None and sidecar.is_file():
        db=None
        try:
            db=sqlite3.connect(sidecar.as_uri()+'?mode=ro',uri=True,timeout=1)
            db.execute('PRAGMA query_only=ON')
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'finance_rules' in tables:
                policy.update({key:int(value) for key,value in db.execute('SELECT key,value FROM finance_rules') if key in policy})
            checkpoints=(save_hash,'%:'+save_hash)
            if 'finance_agreements' in tables:
                query='SELECT payload_json FROM finance_agreements WHERE club=? AND season=? AND (checkpoint=? OR checkpoint LIKE ?)'
                args=(club,season,*checkpoints)
                agreement_rows=db.execute(query+' ORDER BY CASE WHEN competition_id=? THEN 0 ELSE 1 END,start_date DESC',(*args,competition)).fetchall()
                for (raw,) in agreement_rows:
                    try:
                        saved=match_terms(json.loads(raw),match_date or season);candidate=saved.get('rules',{})
                        club_profile=saved.get('club_profile')
                        if candidate:policy.update({key:int(value) for key,value in candidate.items() if key in policy})
                        break
                    except (TypeError,ValueError,json.JSONDecodeError):continue
            session_settings_loaded=False
            if 'session_clubs' in tables:
                row=db.execute('SELECT state_json FROM session_clubs WHERE save_hash=? AND club=? ORDER BY native_io_tick DESC LIMIT 1',(save_hash,club)).fetchone()
                if row:
                    try:
                        settings.update(json.loads(row[0]).get('finance',{}).get('settings',{}));session_settings_loaded=True
                    except (TypeError,ValueError,json.JSONDecodeError):pass
            if 'finance_preferences' in tables and not session_settings_loaded:
                query='SELECT settings_json FROM finance_preferences WHERE club=? AND (checkpoint=? OR checkpoint LIKE ?) ORDER BY CASE WHEN checkpoint=? THEN 0 ELSE 1 END'
                row=db.execute(query,(club,*checkpoints,save_hash)).fetchone()
                if row:
                    try:settings.update(json.loads(row[0]))
                    except (TypeError,ValueError,json.JSONDecodeError):pass
        except (OSError,sqlite3.Error,ValueError,TypeError):
            pass
        finally:
            if db is not None:db.close()
    finance_active=bool(settings.get('enabled',True) and settings.get('tickets',True))
    on_home=home==club and not neutral
    gate=ticket_projection(capacity,prestige,policy,club_profile,occupancy_percent=occupancy_percent)
    if not finance_active or not on_home or capacity<=0:
        gate.update(gross=0,attendance=0,occupancy_bps=0)
    if not finance_active:reason='Bilheteria desativada nas configurações financeiras.'
    elif neutral:reason='Partida em campo neutro; sem bilheteria para o clube.'
    elif home!=club:reason='Jogo fora de casa; bilheteria do clube: 0.'
    elif capacity<=0:reason='Capacidade do estádio indisponível.'
    else:reason='Estimativa pela regra financeira do clube.'
    gate.update(active=finance_active,home=on_home,neutral=neutral,reason=reason)
    return gate


def neutral_fixture(fixture,nodes,game):
    """Use the same competition flags as the finance matchday reader."""
    if game is None:return False
    path=Path(game)/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/settings.txt'
    try:
        with path.open(encoding='utf-8-sig',newline='') as handle:
            neutral={int(row[0]) for row in csv.reader(handle) if len(row)==3 and row[0].isdigit() and row[1]=='match_stadium'}
    except (OSError,UnicodeError):return False
    for start in (fixture[2],fixture[1]):
        node=start;seen=set()
        for _ in range(32):
            if node in seen:break
            seen.add(node)
            if node in neutral:return True
            row=nodes.get(node)
            if row is None or len(row)<2:break
            node=row[1]
    return False


def stadium_preview_key(home,league,game,fallback_image=''):
    settings=stadium_settings(game);pool=settings.get('comp',{}).get(str(league),'') if league>0 else ''
    for token in pool.split(','):
        token=token.strip()
        if not token or all(c in '0123456789' for c in token):break
        return token
    mapping=settings.get('stadium',{}).get(str(home),'').split(',',1)[0].strip()
    return mapping or fallback_image


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
    fallback=club_stadium_fallback(home,game)
    # The Central card uses this generated club catalogue for both capacity
    # and the venue-photo fallback, rather than the shared model stadium row.
    capacity=fallback.get('capacity',0) or (stadium.value('capacity') if stadium is not None and 'capacity' in stadium.fields else 0)
    league=fixture_competition(f,nodes)
    league_name=competition_label(league) if league else ''
    stadium_name,venue_source=stadium_title(home,league,rows,base,stadium_name,game)
    season=f[3]
    calendars=rows('career_calendar')
    if len(calendars)==1:
        try:season=calendars[0].value('startdate')
        except (AttributeError,KeyError,ValueError):pass
    prefs=[r for r in rows('career_managerpref') if r.value('managerprefid')==payload.get('userid')]
    try:currency=int(prefs[0].value('currency')) if len(prefs)==1 else 0
    except (AttributeError,KeyError,TypeError,ValueError):currency=0
    club_profile=teams.get(payload['user']['team_id']) or original.get(payload['user']['team_id'])
    try:prestige=club_profile.value('domesticprestige') if club_profile is not None else 5
    except (AttributeError,KeyError,ValueError):prestige=5
    neutral=neutral_fixture(f,nodes,game)
    crowd_percent=crowd_runtime_percent(game,payload['user']['team_id'],
                                        f[6] if f[5]==payload['user']['team_id'] else f[5],f[3])
    gate=finance_gate(payload.get('save',''),payload.get('save_hash',''),payload['user']['team_id'],
                      season,league,home,neutral,capacity,prestige,f[3],occupancy_percent=crowd_percent)
    expected_attendance=((capacity*crowd_percent+50)//100
                         if capacity>0 and crowd_percent is not None else None)
    image_key=stadium_preview_key(home,league,game,fallback.get('image_key',''))
    from career_currency import currency_symbol
    payload['details']={'date':format_date(f[3]),'time':f'{f[4]//100:02d}:{f[4]%100:02d}',
                        'home_id':home,'home_name':names.get(home,''),'away_name':names.get(f[6],''),
                        'competition_id':league,'competition':league_name or ('Competição '+str(league) if league else 'Calendário da carreira'),
                        'stadium_id':stadium_id,'stadium':stadium_name or 'Não informado',
                        'stadium_image_key':image_key,
                        'location':stadium_location(home,league,game),
                        'capacity':f'{capacity:,}'.replace(',','.') if capacity>0 else 'Não informada',
                        'capacity_value':int(capacity or 0),'crowd_percent':crowd_percent,
                        'expected_attendance':expected_attendance,
                        'currency':currency,'currency_symbol':currency_symbol(currency,game=game),'gate':gate,
                        'venue_source':venue_source,
                        'history_source':'Resultados concluídos desta carreira; do mais recente ao mais antigo.'}
    payload['head_to_head']=head_to_head(snapshot['fixtures'],payload['user']['team_id'],payload['opponent']['team_id'],payload['date'])
    return payload
