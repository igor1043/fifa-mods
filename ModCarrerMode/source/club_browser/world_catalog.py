"""Complete installed team catalog. No hardcoded league/team allowlist.

The original globe TSV supplies its authored names/cities/precise coordinates.
Membership, new leagues and national identities always come from FIFA's DB.
Only generated TSV/JSON cache files are written; the DB and saves are read-only.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,os,re,unicodedata
from lineup_data import FifaDatabase

CONFEDERATIONS={1:'Outras regiões',2:'UEFA',3:'CAF',4:'CONMEBOL',5:'AFC',6:'OFC',7:'CONCACAF'}
FIELDS=('teamid','teamname','latitude','longitude','attackrating','midfieldrating',
        'defenserating','overallrating','internationalprestige','domesticprestige')

def text(value):return str('' if value is None else value).replace('\t',' ').replace('\r',' ').replace('\n',' ')

def folded(value):return ''.join(c for c in unicodedata.normalize('NFKD',str(value)).casefold() if not unicodedata.combining(c))

def league_scope(league,nation,label):
    """National pyramid before regional/federation catalogs, for any country."""
    name=folded(label)
    regional=bool(re.match(r'^fed(?:erac|eraz|erat|[.\s])',name) or re.search(r'\b(?:regional|estadual|provincial)\b',name) or '[off]' in name)
    if regional or league.get('countryid') not in (None,0,nation):return 'regional'
    return 'national' if league.get('leagueid') else 'independent'

def league_label(league,label,scope):
    level=int(league.get('level') or 1)
    if scope=='national' and 1<=level<=4 and 'brasileir' in folded(label):return 'Brasileirão Série '+chr(64+level)
    return label

def read_hints(game):
    hints={}
    for line in (Path(game)/'ModCarrerMode/data/club_browser/catalog.tsv').read_text(encoding='utf8').splitlines():
        v=line.split('\t')
        if len(v)==18:
            try:hints[int(v[9])]=v
            except ValueError:pass
    return hints

def build(game,base=None):
    game=Path(game);base=base or FifaDatabase(game,include_all_tables=True)
    hints=read_hints(game)
    geo=json.loads((game/'ModCarrerMode/data/club_browser/world_geography.json').read_text(encoding='utf8'))
    nations={r['nationid']:r for r in base.rows('nations',['nationid','nationname','isocountrycode','confederation'])}
    leagues={r['leagueid']:r for r in base.rows('leagues',['leagueid','leaguename','countryid','level'])}
    national={r['teamid']:r['nationid'] for r in base.rows('teamnationlinks',['teamid','nationid'])}
    members=Counter(r['teamid'] for r in base.rows('teamplayerlinks',['teamid']))
    links=defaultdict(list)
    for r in base.rows('leagueteamlinks',['teamid','leagueid','secondarytable']):
        if r['leagueid'] in leagues:links[r['teamid']].append(r)
    # ROW clubs have a native, more specific association than the ROW league.
    row_nations={r['teamid']:r['nationid'] for r in base.rows('rowteamnationlinks',['teamid','nationid'])} if 'rowteamnationlinks' in base.tables else {}
    result=[];excluded=[];covered=Counter()
    for team in base.rows('teams',FIELDS):
        ident=team['teamid'];hint=hints.get(ident);is_national=ident in national
        if ident<=0 or (not is_national and not links[ident] and members[ident]<11):
            excluded.append(dict(id=ident,name=team['teamname'],reason='Sem liga nem elenco jogável'));continue
        candidates=sorted(links[ident],key=lambda r:(bool(r['secondarytable']),r['leagueid']))
        old_league=int(hint[5]) if hint else 0
        link=next((r for r in candidates if r['leagueid']==old_league),candidates[0] if candidates else None)
        league=leagues.get(link['leagueid'],{}) if link else {}
        nation=national.get(ident) if is_national else int(hint[2]) if hint else row_nations.get(ident,league.get('countryid',0))
        country=nations.get(nation,{})
        geography=geo.get(country.get('isocountrycode',''),{})
        lat,lon=float(team.get('latitude') or 0),float(team.get('longitude') or 0)
        if hint:lat,lon=float(hint[12]),float(hint[13])
        elif lat==lon==0:lat,lon=geography.get('lat',0),geography.get('lon',0)
        confed=int(country.get('confederation') or 1)
        label=hint[6] if hint and old_league==league.get('leagueid') else league.get('leaguename','Clubes independentes')
        scope=league_scope(league,nation,label)
        row=dict(id=ident,name=(country.get('nationname') if is_national else hint[10] if hint else team['teamname']) or team['teamname'],
            kind='nations' if is_national else 'clubs',nation=nation or 0,
            country=confed if is_national else int(hint[0]) if hint else nation or 0,
            countryName=CONFEDERATIONS.get(confed,'Outras regiões') if is_national else hint[1] if hint else country.get('nationname','Outros países'),
            world=int(hint[3]) if hint else geography.get('world',0),
            league=10000+confed if is_national else league.get('leagueid',9999),
            leagueName='Seleções nacionais' if is_national else league_label(league,label,scope),leagueScope='national' if is_national else scope,
            level=1 if is_national else max(1,int(league.get('level') or 1)),
            city=country.get('nationname','') if is_national else hint[11] if hint else '',lat=lat,lon=lon,confederation=confed,
            attack=team.get('attackrating') or 0,midfield=team.get('midfieldrating') or 0,
            defense=team.get('defenserating') or 0,overall=team.get('overallrating') or 0,
            international=team.get('internationalprestige') or 0,domestic=team.get('domesticprestige') or 0)
        result.append(row)
        if link:covered[link['leagueid']]+=1
    result.sort(key=lambda r:(r['kind'],folded(r['countryName']),{'national':0,'regional':1,'independent':2}[r['leagueScope']],r['level'] if r['leagueScope']=='national' else 0,folded(r['leagueName']),r['league'],folded(r['name']),r['id']))
    orders={};counts=Counter()
    for row in result:
        key=(row['kind'],row['country'],row['league'])
        if key not in orders:
            country=key[:2];counts[country]+=1;orders[key]=counts[country]
        row['leagueOrder']=orders[key]
    audit=dict(sourceTeams=base.tables['teams']['rows'],clubs=sum(r['kind']=='clubs' for r in result),nations=sum(r['kind']=='nations' for r in result),excluded=excluded,
        missingTeams=sorted(set(r['teamid'] for r in base.rows('teams',['teamid']))-{r['id'] for r in result}-{r['id'] for r in excluded}),
        missingLeagues=[dict(id=k,name=v['leaguename']) for k,v in leagues.items() if any(r['leagueid']==k for values in links.values() for r in values) and not covered[k]],
        geographicFallbacks=[r['id'] for r in result if r['lat']==r['lon']==0])
    return result,audit

def tsv(rows,kind):
    out=[]
    for i,r in enumerate(r for r in rows if r['kind']==kind):
        out.append('\t'.join(map(text,(r['country'],r['countryName'],r['nation'],r['world'],r.get('leagueOrder',r['level']),r['league'],r['leagueName'],r['level'],i,r['id'],r['name'],r['city'],r['lat'],r['lon'],r['attack'],r['midfield'],r['defense'],r['overall']))))
    return ('\n'.join(out)+'\n').encode('utf8')

def ensure(game):
    game=Path(game);folder=game/'ModCarrerMode/runtime/club_browser/catalog'
    inputs=[game/'data/db/fifa_ng_db.db',game/'data/db/fifa_ng_db-meta.xml',game/'ModCarrerMode/data/club_browser/catalog.tsv',game/'ModCarrerMode/data/club_browser/world_geography.json',Path(__file__)]
    stamp=hashlib.sha256(str([(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in inputs]).encode()).hexdigest()
    state=folder/'ready.json'
    if state.is_file():
        try:
            if json.loads(state.read_text())['stamp']==stamp and all((folder/n).is_file() for n in ('catalog.tsv','nations.tsv')):return folder
        except (OSError,ValueError,KeyError):pass
    rows,audit=build(game);folder.mkdir(parents=True,exist_ok=True)
    def atomic(name,blob):
        target=folder/name;temp=target.with_name(target.name+'.'+str(os.getpid())+'.new');temp.write_bytes(blob);os.replace(temp,target)
    atomic('catalog.tsv',tsv(rows,'clubs'));atomic('nations.tsv',tsv(rows,'nations'))
    atomic('ready.json',json.dumps(dict(stamp=stamp,**audit),ensure_ascii=False,indent=2).encode('utf8'))
    return folder
