"""Read confirmed career cups without running or waiting for the coach market.

The save identifies the career and supplies its schedule/manager metadata. The
owner-thread publication supplies unsaved scores. Nothing writes DATA or SQL.
"""
from pathlib import Path
import copy,hashlib,json,sys

_browser=str(Path(__file__).resolve().parents[2]/'club_browser')
if _browser not in sys.path:sys.path.insert(0,_browser)

_projection=None
_last=None


def completed_titles(fixtures,formats,leagues,today,season,label):
    from title_evidence import completed_titles as evidence
    return evidence(fixtures,formats,leagues,today,season,label)


def merge_scores(saved,snapshot,season):
    from title_evidence import merge_scores as evidence
    return evidence(saved,snapshot,season)


def read(game,snapshot,collection='club'):
    global _projection,_last
    if collection not in ('club','coach'):raise ValueError('Acervo inválido')
    from career_publication import read as publication
    from lineup_data import ProjectionCache
    from competition_schedule import read_schedule
    from competition_formats import read_formats
    from manager_market.competition_labels import resolve
    game=Path(game);save=Path(str(snapshot['savePath']).removeprefix('\\\\?\\')).resolve()
    owner=dict(path=snapshot['savePath'],pid=snapshot['pid'],process_created_100ns=snapshot['processCreated100ns'])
    current=publication(game,owner,snapshot['date'],epoch=snapshot['fceContextEpoch'],club=snapshot['club'])
    if current is None:raise ValueError('Aguardando resultados da carreira atual')
    # Include the score content, not merely a frequently refreshed timestamp.
    signature=hashlib.sha256(json.dumps([current['nodes'],current['fixtures']],separators=(',',':')).encode()).hexdigest()
    stat=save.stat();key=(str(game.resolve()),str(save),stat.st_size,stat.st_mtime_ns,
        current['pid'],current['processCreated100ns'],current['fceContextEpoch'],current['club'],current['date'],signature,collection)
    if _last and _last[0]==key:return copy.deepcopy(_last[1]),_last[2]
    if _projection is None:_projection=ProjectionCache()
    raw,dbs,base=_projection.load(game,save)
    def rows(name,fields):
        choices=[d for d in dbs if name in d.tables]
        if len(choices)!=1:raise ValueError('Metadados de carreira incompletos: '+name)
        return choices[0].rows(name,[f for f in fields if f in choices[0].tables[name]['fields']])
    calendars=rows('career_calendar',['startdate','currdate']);users=rows('career_users',['clubteamid','seasoncount','userid','usertype','nationalteamid'])
    if len(calendars)!=1 or len(users)!=1 or users[0].get('usertype')!=1:raise ValueError('Aguardando carreira de treinador')
    cal,user=calendars[0],users[0]
    if user['clubteamid']!=current['club'] or cal['currdate']>current['date']:raise ValueError('A carreira mudou durante a leitura')
    history=rows('career_managerhistory',['teamid','season'])
    from title_evidence import career_start
    first=career_start(cal,user)
    employers={}
    for row in history:employers.setdefault(row['season'],set()).add(row['teamid'])
    definitions={r['leagueid']:r for r in base.rows('leagues',['leagueid','leaguename','level']) if r['level']>0}
    links=rows('leagueteamlinks',['teamid','leagueid','secondarytable'])
    leagues={i:dict(name=r['leaguename'],members={r['teamid'] for r in links if r['leagueid']==i and r['secondarytable']==0}) for i,r in definitions.items()}
    formats=read_formats(game);fixtures=merge_scores(read_schedule(raw,formats),current,first)
    titles=completed_titles(fixtures,formats,leagues,current['date'],first,lambda i:resolve(game,i,definitions.get(i,{}).get('leaguename','')))
    # The club collection never receives international titles. For the native
    # fallback, a national job is proven from this saved date onward only; the
    # durable ledger handles earlier/later dated national appointments.
    nation=user.get('nationalteamid',0)
    national_ids={r['teamid'] for r in base.rows('teamnationlinks',['teamid'])}
    def owned(t):
        ordinal=t['season']//10000-first//10000+1
        club_title=employers.get(ordinal)=={t['club']} and (collection=='coach' or t['club']==current['club'])
        national_title=collection=='coach' and nation in national_ids and t['club']==nation and t['date']>=cal['currdate']
        return club_title or national_title
    titles=[dict(t,team_kind='national' if t['club'] in national_ids else 'club') for t in titles if owned(t)]
    branch='native-'+hashlib.sha256((str(save)+_projection.save_hash+str(key[4:])).encode()).hexdigest()[:24]
    if ProjectionCache.identity(save)[2:]!=(stat.st_size,stat.st_mtime_ns):raise InterruptedError('O save mudou durante a leitura das conquistas')
    _last=(key,copy.deepcopy(titles),branch)
    return titles,branch
