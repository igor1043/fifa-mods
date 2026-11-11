"""Read titles from the current, validated career branch; never write SQL/save data."""
from pathlib import Path
import configparser,json,sqlite3
from contextlib import closing


def same_path(a,b):
    return Path(str(a).removeprefix('\\\\?\\')).resolve()==Path(str(b).removeprefix('\\\\?\\')).resolve()


def title_rows(game,snapshot,collection='club'):
    pending=None
    try:rows,branch=market_title_rows(game,snapshot,collection)
    except (OSError,ValueError,KeyError,sqlite3.Error) as error:pending=error
    # Native confirmed wins remain authoritative even when the coach journal
    # was first enabled/recovered after this season's trophies were earned.
    from .native_titles import read
    try:native,native_branch=read(game,snapshot,collection)
    except (OSError,ValueError,KeyError,sqlite3.Error):
        if pending:raise pending
        return rows,branch
    if pending:return native,native_branch
    known={(r['year'],r['root'],r['club']) for r in rows}
    additions=[r for r in native if (r['year'],r['root'],r['club']) not in known]
    return (rows+additions,branch+':'+native_branch) if additions else (rows,branch)


def market_title_rows(game,snapshot,collection='club'):
    """A publication from another save, rewind, process or epoch is never reused."""
    game=Path(game)
    publication=game/'ModCarrerMode/runtime/manager_market/state_ready.json'
    raw=publication.read_bytes();state=json.loads(raw)
    expected=dict(pid=snapshot['pid'],created=snapshot['processCreated100ns'],
                  epoch=snapshot['fceContextEpoch'],club=snapshot['club'],date=snapshot['date'])
    if any(state.get(k)!=v for k,v in expected.items()) or not same_path(state['save'],snapshot['savePath']):
        raise ValueError('Aguardando os títulos da carreira atual')
    database=Path(state['database']).resolve()
    # The existing market sidecar is associated with this exact career folder.
    if database.parent!=Path(str(snapshot['savePath']).removeprefix('\\\\?\\')).resolve().parent:
        raise ValueError('Banco de títulos pertence a outra carreira')
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=.4)) as db:
        db.row_factory=sqlite3.Row
        db.execute('BEGIN')
        branch=db.execute('SELECT * FROM branches WHERE id=?',(state['branch'],)).fetchone()
        if not branch or branch['game_date']!=snapshot['date'] or branch['user_club']!=snapshot['club']:
            raise ValueError('Os títulos ainda estão sendo atualizados')
        if collection not in ('club','coach'):raise ValueError('Acervo inválido')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns={r[1] for r in db.execute('PRAGMA table_info(honours)')}
        coach=None
        if 'appointments' in tables and 'coach_id' in columns:
            row=db.execute("SELECT coach_id FROM appointments WHERE branch=? AND club_id=? AND coach_id LIKE 'USER-%' AND start_date<=? AND (end_date IS NULL OR end_date>=?) ORDER BY start_date DESC LIMIT 1",
                (state['branch'],snapshot['club'],snapshot['date'],snapshot['date'])).fetchone()
            if row:coach=row[0]
        if not coach and 'coach_id' in columns:
            owners=[r[0] for r in db.execute("SELECT DISTINCT coach_id FROM honours WHERE branch=? AND coach_id LIKE 'USER-%' AND game_date<=?",(state['branch'],snapshot['date']))]
            if len(owners)==1:coach=owners[0]
        where='branch=? AND game_date<=?';params=[state['branch'],snapshot['date']]
        if collection=='club':where+=' AND club_id=?';params.append(snapshot['club'])
        if coach:where+=' AND coach_id=?';params.append(coach)
        elif collection=='coach' or 'coach_id' in columns:where+=' AND 0'
        sources=['trophy_history','honours'] if 'trophy_history' in tables else ['honours']
        rows=[]
        for table in sources:rows.extend(dict(r) for r in db.execute('SELECT * FROM '+table+' WHERE '+where+' ORDER BY game_date DESC,root',params))
    if publication.read_bytes()!=raw:raise InterruptedError('A carreira mudou durante a leitura dos títulos')
    unique={}
    for r in rows:
        key=(r['game_date']//10000,r['root'],r['competition_id'],r['club_id'])
        if key in unique:continue
        unique[key]=dict(competition=int(r['competition_id']),root=int(r['root']),season=int(r['season']),
                         date=int(r['game_date']),year=int(r['game_date'])//10000,
                         name=r['name'],club=int(r['club_id']),coach=r.get('coach_id',coach),team_kind=r.get('team_kind','club'),origin='career')
    return list(unique.values()),state['branch']


def trophy_id(competition,root,catalogue,exists):
    """cz_leagues.trophyid wins. No unrelated/default cup is substituted."""
    for key in (root,competition):
        value=catalogue.get(int(key))
        if value and exists(int(value)):return int(value)
    # root may be an internal FCE node whose numeric ID happens to collide
    # with another competition's trophy. Only the verified visual ID is safe.
    for key in (competition,):
        if key>0 and exists(int(key)):return int(key)
    return 0


def page_rows(rows,page,capacity=30):
    ordered=sorted(rows,key=lambda r:(-r['date'],r['competition'],r['root']))
    pages=max(1,(len(ordered)+capacity-1)//capacity)
    page=max(0,min(int(page),pages-1))
    return ordered[page*capacity:(page+1)*capacity],page,pages


def grouped_titles(rows):
    """Three wins in a competition share a cup; retain every winning club/date."""
    groups={}
    for source in rows:
        row=dict(source)
        groups.setdefault((int(row['competition']),row.get('origin','career')),[]).append(row)
    result=[]
    for victories in groups.values():
        victories.sort(key=lambda r:(-r['date'],r.get('club',0),r['root']))
        for wins in ([victories] if len(victories)>=3 else [[r] for r in victories]):
            row=dict(wins[0]);years=[int(w['year']) for w in wins]
            row.update(wins=[dict(w) for w in wins],title_count=len(wins),first_year=min(years),last_year=max(years))
            result.append(row)
    return sorted(result,key=lambda r:(-r['date'],r['competition'],r['root']))


def custom_available(game,club):
    return (Path(game)/'ModCarrerMode/data/trophy_room/custom'/str(int(club))/'identity-wall.png').is_file()


def appearance(game,club):
    config=configparser.ConfigParser()
    config.read(Path(game)/'ModCarrerMode/config/trophy_room.ini',encoding='utf8')
    choice=config.get(str(club),'style',fallback='custom' if custom_available(game,club) else 'default')
    return 'custom' if choice=='custom' and custom_available(game,club) else 'default'


def demo_rows(game,club,year):
    """Explicit local preview only. These rows are never persisted as honours."""
    config=configparser.ConfigParser()
    config.read(Path(game)/'ModCarrerMode/config/trophy_room.ini',encoding='utf8')
    if not config.getboolean(str(club),'preview_trophies',fallback=False):return []
    samples=((1003,'CONMEBOL Libertadores'),(7,'Brasileirão'),(229,'Copa do Brasil'),
             (9,'Supercopa'),(23,'Campeonato estadual'),(1009,'CONMEBOL Recopa'))
    return [dict(competition=i,root=i,date=year*10000+101,year=year,
                 name=name+' · DEMONSTRAÇÃO',origin='preview') for i,name in samples
            if (Path(game)/f'data/sceneassets/trophy/trophy_{i}.rx3').is_file()]
