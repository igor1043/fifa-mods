"""Complete installed team catalog. No hardcoded league/team allowlist.

The original globe TSV supplies its authored names/cities/precise coordinates.
Membership, new leagues and national identities always come from FIFA's DB.
Only generated TSV/JSON cache files are written; the DB and saves are read-only.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,os,re,unicodedata
from lineup_data import FifaDatabase
import catalog_overrides

CONFEDERATIONS={1:'Outras regiões',2:'UEFA',3:'CAF',4:'CONMEBOL',5:'AFC',6:'OFC',7:'CONCACAF'}
FIELDS=('teamid','teamname','latitude','longitude','attackrating','midfieldrating',
        'defenserating','overallrating','internationalprestige','domesticprestige')

def text(value):return str('' if value is None else value).replace('\t',' ').replace('\r',' ').replace('\n',' ')

def folded(value):return ''.join(c for c in unicodedata.normalize('NFKD',str(value)).casefold() if not unicodedata.combining(c))

def league_scope(league,nation,label):
    """National pyramid before regional/federation catalogs, for any country."""
    name=folded(label)
    regional=bool(re.match(r'^fed(?:erac|eraz|erat|[.\s])',name) or re.search(r'\b(?:regional|estadual|provincial)\b',name) or '[off]' in name)
    if regional:return 'regional'
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
    overrides,override_warnings=catalog_overrides.load(game)
    geo=json.loads((game/'ModCarrerMode/data/club_browser/world_geography.json').read_text(encoding='utf8'))
    nations={r['nationid']:r for r in base.rows('nations',['nationid','nationname','isocountrycode','confederation'])}
    leagues={r['leagueid']:r for r in base.rows('leagues',['leagueid','leaguename','countryid','level'])}
    # One country ID has one display name, including newly added clubs without
    # a translated TSV hint. A stale ROW link must not split a domestic league.
    names=defaultdict(Counter)
    for hint in hints.values():names[int(hint[2])][hint[1]]+=1
    def country_name(ident):
        return overrides['country'].get(ident,{}).get('name') or geo.get(nations.get(ident,{}).get('isocountrycode',''),{}).get('name') or (names[ident].most_common(1)[0][0] if names[ident] else nations.get(ident,{}).get('nationname','Outros países'))
    def country_geo(ident):
        value=dict(geo.get(nations.get(ident,{}).get('isocountrycode',''),{}))
        for key,value_key in (('world_id','world'),('latitude','lat'),('longitude','lon')):
            if key in overrides['country'].get(ident,{}):value[value_key]=overrides['country'][ident][key]
        return value
    for kind,known in (('club',{r['teamid'] for r in base.rows('teams',['teamid'])}),('country',nations),('league',leagues)):
        for ident in set(overrides[kind])-set(known):override_warnings.append(kind+':'+str(ident)+': ID não encontrado nesta DB')
    for ident,values in overrides['league'].items():
        if ident not in leagues:continue
        if 'country_id' in values and values['country_id'] in nations:leagues[ident]=dict(leagues[ident],countryid=values['country_id'])
    national={r['teamid']:r['nationid'] for r in base.rows('teamnationlinks',['teamid','nationid'])}
    members=Counter(r['teamid'] for r in base.rows('teamplayerlinks',['teamid']))
    links=defaultdict(list)
    for r in base.rows('leagueteamlinks',['teamid','leagueid','secondarytable']):
        if r['leagueid'] in leagues:links[r['teamid']].append(r)
    # ROW clubs have a native, more specific association than the ROW league.
    row_nations={r['teamid']:r['nationid'] for r in base.rows('rowteamnationlinks',['teamid','nationid'])} if 'rowteamnationlinks' in base.tables else {}
    # Expanded clubs often leave team summary ratings at zero. Derive missing
    # summaries from their real squad, grouped by the player's primary role.
    players={r['playerid']:r for r in (base.rows('players',['playerid','overallrating','preferredposition1']) if 'players' in base.tables else [])}
    squad=defaultdict(list)
    for r in base.rows('teamplayerlinks',['teamid','playerid']):
        player=players.get(r['playerid'])
        if player and 1<=player['overallrating']<=99:squad[r['teamid']].append(player)
    def rating(ident,group):
        positions={'attack':set(range(20,28)),'midfield':set(range(10,20)),'defense':set(range(1,10))}
        roster=squad[ident];values=sorted((r['overallrating'] for r in roster if group=='overall' or r['preferredposition1'] in positions[group]),reverse=True)
        if not values:values=sorted((r['overallrating'] for r in roster if r['preferredposition1']!=0),reverse=True)
        values=values[:11 if group=='overall' else 4]
        return round(sum(values)/len(values)) if values else 0
    result=[];excluded=[];covered=Counter()
    for team in base.rows('teams',FIELDS):
        ident=team['teamid'];hint=hints.get(ident);is_national=ident in national
        if ident<=0 or (not is_national and not links[ident] and members[ident]<11):
            excluded.append(dict(id=ident,name=team['teamname'],reason='Sem liga nem elenco jogável'));continue
        candidates=sorted(links[ident],key=lambda r:(bool(r['secondarytable']),r['leagueid']))
        # A previous display hint must not override a new primary membership.
        # Expanded databases can move a ROW club into its own domestic league.
        primary=[r for r in candidates if not r['secondarytable']]
        if primary:candidates=primary
        old_league=int(hint[5]) if hint else 0
        link=next((r for r in candidates if r['leagueid']==old_league),candidates[0] if candidates else None)
        league=leagues.get(link['leagueid'],{}) if link else {}
        club_override=overrides['club'].get(ident,{}) if not is_national else {}
        league_override=overrides['league'].get(league.get('leagueid'),{})
        league_nation=league.get('countryid')
        # rowteamnationlinks is authoritative for ROW/independent clubs only.
        # Reused IDs retain old links even after moving into a domestic league.
        domestic=bool(nations.get(league_nation,{}).get('isocountrycode') and league_override.get('scope')!='independent')
        nation=national.get(ident) if is_national else (league_nation if domestic else row_nations.get(ident) or league_nation or (int(hint[2]) if hint else 0))
        if 'country_id' in club_override:
            if club_override['country_id'] in nations:nation=club_override['country_id']
            else:override_warnings.append('club:'+str(ident)+': country_id não encontrado; mantida associação da DB')
        if nation not in nations and not is_national:
            excluded.append(dict(id=ident,name=team['teamname'],reason='Liga interna sem país nem associação nacional'));continue
        country=nations.get(nation,{})
        geography=country_geo(nation)
        same_identity=bool(hint and old_league==league.get('leagueid') and (int(hint[2])==nation or int(hint[3])==geography.get('world',-1)>0))
        lat,lon=float(team.get('latitude') or 0),float(team.get('longitude') or 0)
        if same_identity:lat,lon=float(hint[12]),float(hint[13])
        elif lat==lon==0:lat,lon=geography.get('lat',0),geography.get('lon',0)
        if is_national and 'latitude' in overrides['country'].get(nation,{}):lat,lon=geography['lat'],geography['lon']
        city=country_name(nation) if is_national else hint[11] if same_identity else ''
        if 'latitude' in club_override:
            lat,lon=club_override['latitude'],club_override['longitude']
        if 'city' in club_override:city=club_override['city']
        # State federation IDs repurpose foreign country slots in this patch.
        # Preserve accurate Brazilian club hints; otherwise identify a state
        # location explicitly as approximate rather than placing it overseas.
        if league_override.get('state') and nation==54 and not (-34<=lat<=6 and -74<=lon<=-34):
            lat,lon=league_override.get('latitude',geography.get('lat',0)),league_override.get('longitude',geography.get('lon',0))
            city='Localização aproximada · '+league_override['state']
        confed=int(country.get('confederation') or 1)
        label=league_override.get('name') or (hint[6] if hint and old_league==league.get('leagueid') else league.get('leaguename','Clubes independentes'))
        scope=league_override.get('scope') or league_scope(league,nation,label)
        level=max(1,int(league.get('level') or 1))
        subtitle=league_override.get('division_label') or ('Federação estadual' if scope=='regional' else 'Competição internacional' if scope=='international' else 'Clubes independentes' if scope=='independent' else str(level)+'ª divisão'+(' · '+country_name(league_nation) if league_nation and league_nation!=nation else ''))
        display_name=country_name(nation) if is_national else club_override.get('name') or (hint[10] if same_identity else team['teamname'])
        row=dict(id=ident,name=display_name or team['teamname'],
            kind='nations' if is_national else 'clubs',nation=nation or 0,
            country=confed if is_national else nation or 0,
            countryName=CONFEDERATIONS.get(confed,'Outras regiões') if is_national else country_name(nation),
            world=club_override.get('world_id',overrides['country'].get(nation,{}).get('world_id',int(hint[3]) if same_identity else geography.get('world',0))),
            league=10000+confed if is_national else league.get('leagueid',9999),
            leagueName='Seleções nacionais' if is_national else league_label(league,label,scope),leagueScope='national' if is_national else scope,
            level=1 if is_national else level,divisionLabel='Seleções nacionais' if is_national else subtitle,
            state=club_override.get('state',league_override.get('state','')),
            city=city,lat=lat,lon=lon,confederation=confed,
            attack=team.get('attackrating') or rating(ident,'attack'),midfield=team.get('midfieldrating') or rating(ident,'midfield'),
            defense=team.get('defenserating') or rating(ident,'defense'),overall=team.get('overallrating') or rating(ident,'overall'),
            international=team.get('internationalprestige') or 0,domestic=team.get('domesticprestige') or 0)
        result.append(row)
        if link:covered[link['leagueid']]+=1
    result.sort(key=lambda r:(r['kind'],folded(r['countryName']),{'national':0,'regional':1,'international':2,'independent':3}[r['leagueScope']],r['level'] if r['leagueScope']=='national' else 0,folded(r['leagueName']),r['league'],folded(r['name']),r['id']))
    orders={};counts=Counter()
    for row in result:
        key=(row['kind'],row['country'],row['league'])
        if key not in orders:
            country=key[:2];counts[country]+=1;orders[key]=counts[country]
        row['leagueOrder']=orders[key]
    audit=dict(sourceTeams=base.tables['teams']['rows'],clubs=sum(r['kind']=='clubs' for r in result),nations=sum(r['kind']=='nations' for r in result),excluded=excluded,
        missingTeams=sorted(set(r['teamid'] for r in base.rows('teams',['teamid']))-{r['id'] for r in result}-{r['id'] for r in excluded}),
        missingLeagues=[dict(id=k,name=v['leaguename']) for k,v in leagues.items() if any(r['leagueid']==k for values in links.values() for r in values) and not covered[k]],
        geographicFallbacks=[r['id'] for r in result if r['lat']==r['lon']==0],overrideWarnings=override_warnings)
    return result,audit

def tsv(rows,kind,metadata=False):
    out=[]
    for i,r in enumerate(r for r in rows if r['kind']==kind):
        values=(r['country'],r['countryName'],r['nation'],r['world'],r.get('leagueOrder',r['level']),r['league'],r['leagueName'],r['level'],i,r['id'],r['name'],r['city'],r['lat'],r['lon'],r['attack'],r['midfield'],r['defense'],r['overall'])
        if metadata:values+=r.get('divisionLabel',''),
        out.append('\t'.join(map(text,values)))
    return ('\n'.join(out)+'\n').encode('utf8')

def ensure(game):
    game=Path(game);folder=game/'ModCarrerMode/runtime/club_browser/catalog'
    inputs=[game/'data/db/fifa_ng_db.db',game/'data/db/fifa_ng_db-meta.xml',game/'ModCarrerMode/data/club_browser/catalog.tsv',game/'ModCarrerMode/data/club_browser/world_geography.json',game/catalog_overrides.RELATIVE,Path(catalog_overrides.__file__),Path(__file__)]
    stamp=hashlib.sha256(str([(str(p),p.stat().st_size,p.stat().st_mtime_ns) if p.is_file() else (str(p),None) for p in inputs]).encode()).hexdigest()
    state=folder/'ready.json'
    if state.is_file():
        try:
            if json.loads(state.read_text())['stamp']==stamp and all((folder/n).is_file() for n in ('catalog.tsv','nations.tsv')):return folder
        except (OSError,ValueError,KeyError):pass
    rows,audit=build(game);folder.mkdir(parents=True,exist_ok=True)
    def atomic(name,blob):
        target=folder/name;temp=target.with_name(target.name+'.'+str(os.getpid())+'.new');temp.write_bytes(blob);os.replace(temp,target)
    atomic('catalog.tsv',tsv(rows,'clubs',metadata=True));atomic('nations.tsv',tsv(rows,'nations',metadata=True))
    atomic('ready.json',json.dumps(dict(stamp=stamp,**audit),ensure_ascii=False,indent=2).encode('utf8'))
    return folder
