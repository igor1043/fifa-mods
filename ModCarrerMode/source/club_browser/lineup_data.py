"""Read-only starting XI projection for the club viewer's group photograph."""
from pathlib import Path
import hashlib,struct,sys,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'club_environment/market'))
from fifa_db import FifaDatabase

APPEARANCE=('headtypecode','headclasscode','hairtypecode','haircolorcode','skintonecode','skintypecode','facialhairtypecode','facialhaircolorcode','shoetypecode','shoedesigncode','gender','height','weight','bodytypecode','eyecolorcode','eyebrowcode','sideburnscode','jerseysleevelengthcode','jerseyfit','jerseystylecode','socklengthcode','shortstyle','gkglovetypecode')
ATTRIBUTES=('acceleration','sprintspeed','agility','reactions','balance','shotpower','finishing','longshots','volleys','penalties','vision','crossing','shortpassing','longpassing','curve','freekickaccuracy','ballcontrol','dribbling','strength','stamina','jumping','aggression','interceptions','positioning','marking','standingtackle','slidingtackle','headingaccuracy','gkdiving','gkhandling','gkkicking','gkpositioning','gkreflexes','potential')

class ProjectionCache:
    """One active save, invalidated by save/DB/schema file identity and revision.

    Immutable parsed tables and projected fixtures are shared by successive club
    selections. This cache is never written to the career save or its SQL data.
    """
    def __init__(self):
        self.signature=None;self.raw=None;self.dbs=None;self.base=None
        self.rows={};self.indices={};self.results={};self.save_hash=None
    @staticmethod
    def identity(path):
        path=Path(path).resolve();stat=path.stat()
        return str(path),stat.st_ino,stat.st_size,stat.st_mtime_ns
    def load(self,game,save):
        signature=tuple(self.identity(p) for p in (save,game/'data/db/fifa_ng_db.db',game/'data/db/fifa_ng_db-meta.xml'))
        if signature!=self.signature:
            raw=Path(save).read_bytes();dbs=databases(raw,game);base=FifaDatabase(game,include_all_tables=True)
            if signature!=tuple(self.identity(p) for p in (save,game/'data/db/fifa_ng_db.db',game/'data/db/fifa_ng_db-meta.xml')):raise ValueError('O save mudou durante a leitura dos titulares.')
            self.raw,self.dbs,self.base=raw,dbs,base;self.signature=signature
            self.rows.clear();self.indices.clear();self.results.clear();self.save_hash=hashlib.sha256(raw).hexdigest()
        return self.raw,self.dbs,self.base
    def table(self,db,name,fields):
        key=(id(db),name,tuple(fields))
        if key not in self.rows:self.rows[key]=db.rows(name,fields)
        return self.rows[key]
    def matching(self,db,name,fields,key,values):
        index_key=(id(db),name,key);table=db.tables[name]
        if index_key not in self.indices:
            index={}
            for row in range(table['rows']):index.setdefault(db.value(table,row,key),[]).append(row)
            self.indices[index_key]=index
        index=self.indices[index_key]
        return [{f:db.value(table,row,f) for f in fields} for value in values for row in index.get(value,())]

def databases(raw,game):
    if len(raw)<180 or raw[116:132]!=b'SaveType_Career\0' or struct.unpack_from('<I',raw,132)[0]!=zlib.crc32(raw[160:]):raise ValueError('O save da carreira não passou na verificação de integridade.')
    spans=[];at=160
    while True:
        at=raw.find(b'DB\0\x08',at)
        if at<0:break
        size=struct.unpack_from('<I',raw,at+8)[0]
        if 24<=size<=len(raw)-at:spans.append((at,size));at+=size
        else:at+=4
    if len(spans)!=3:raise ValueError('Estrutura de carreira não reconhecida.')
    return [FifaDatabase(game,raw[at:at+size],include_all_tables=True) for at,size in spans]

def starting_sheet(rows,club,members):
    candidates=[r for r in rows('teamsheets',['teamid','isfavourite',*('playerid'+str(i) for i in range(11)),*('position'+str(i) for i in range(11))]) if r['teamid']==club and r.get('isfavourite')==1]
    if not candidates:candidates=[r for r in rows('default_teamsheets',['teamid',*('playerid'+str(i) for i in range(11)),*('position'+str(i) for i in range(11))]) if r['teamid']==club]
    if len(candidates)!=1:raise ValueError('O clube não tem uma escalação titular única neste save.')
    sheet=candidates[0];ids=[sheet['playerid'+str(i)] for i in range(11)]
    if len(set(ids))!=11 or any(p not in members for p in ids):raise ValueError('A escalação não tem 11 jogadores distintos vinculados a este clube.')
    return [(int(sheet.get('position'+str(i)) or 0),members[p]) for i,p in enumerate(ids)]

def pack_fixture(club,name,team,players,lineup,names,edited):
    if len(lineup)!=11 or len({r['playerid'] for _,r in lineup})!=11:raise ValueError('São necessários 11 titulares reais.')
    out=bytearray(struct.pack('<8sIII128s',b'C3DQA003',11,club,420,name.encode('utf8')[:127].ljust(128,b'\0')))
    color=sum(int(team.get('teamcolor1'+ch) or 0)<<shift for ch,shift in zip('rgb',(16,8,0)))
    def value(row,key,default=-1):return int(row[key]) if row.get(key) is not None else default
    roster=[]
    for slot,link in lineup:
        p=players[link['playerid']];appearance=[value(p,f) for f in APPEARANCE]
        if not 130<=appearance[11]<=230:raise ValueError('Altura do jogador não foi encontrada na carreira.')
        custom=edited.get(p['playerid'],{});label=custom.get('playerjerseyname') or custom.get('commonname') or names.get(p.get('commonnameid')) or ' '.join(filter(None,[custom.get('firstname') or names.get(p.get('firstnameid')),custom.get('surname') or names.get(p.get('lastnameid'))]))
        if not label:label='Jogador '+str(p['playerid'])
        encoded=label.encode('utf8')[:127]
        while encoded:
            try:encoded.decode('utf8');break
            except UnicodeDecodeError:encoded=encoded[:-1]
        fields=[p['playerid'],club,value(link,'jerseynumber',0),value(p,'preferredposition1'),-1,value(p,'overallrating'),*appearance]
        out.extend(struct.pack('<29i4I34i128s6i',*fields,color,color,color,1,*(value(p,f) for f in ATTRIBUTES),encoded.ljust(128,b'\0'),int(p['playerid']==team.get('captainid')),slot,*(value(p,'preferredposition'+str(i)) for i in (2,3,4)),1))
        roster.append(dict(id=p['playerid'],name=label,number=value(link,'jerseynumber',0),position=slot,overall=value(p,'overallrating')))
    return bytes(out),roster

def project(game,save,club,cache=None):
    game=Path(game)
    if cache:
        raw,dbs,base=cache.load(game,save)
        if club in cache.results:return cache.results[club]
    else:raw=Path(save).read_bytes();dbs=databases(raw,game);base=FifaDatabase(game,include_all_tables=True)
    def rows(name,fields):
        matches=[db for db in dbs if name in db.tables]
        if len(matches)>1:raise ValueError('Tabela ambígua: '+name)
        db=matches[0] if matches else base if name in base.tables else None
        return (cache.table(db,name,fields) if cache else db.rows(name,fields)) if db else []
    def matching(db,name,fields,key,values):return cache.matching(db,name,fields,key,values) if cache else db.rows_matching(name,fields,key,values)
    teams=[t for t in rows('teams',['teamid','teamname','teamcolor1r','teamcolor1g','teamcolor1b','captainid']) if t['teamid']==club]
    if len(teams)!=1:raise ValueError('Clube não encontrado no save ativo.')
    team=teams[0]
    members={r['playerid']:r for r in rows('teamplayerlinks',['teamid','playerid','position','jerseynumber']) if r['teamid']==club}
    lineup=starting_sheet(rows,club,members);ids={r['playerid'] for _,r in lineup}
    fields=['playerid','commonnameid','firstnameid','lastnameid','preferredposition1','preferredposition2','preferredposition3','preferredposition4','overallrating',*APPEARANCE,*ATTRIBUTES]
    fields=list(dict.fromkeys(fields));matches=[db for db in dbs if 'players' in db.tables]
    if len(matches)!=1:raise ValueError('Jogadores da carreira indisponíveis.')
    players={p['playerid']:p for p in matching(base,'players',fields,'playerid',ids)}
    for p in matching(matches[0],'players',fields,'playerid',ids):players.setdefault(p['playerid'],{}).update({k:v for k,v in p.items() if v is not None})
    if ids-set(players):raise ValueError('Um dos titulares não está disponível no save.')
    wanted={p.get(key) for p in players.values() for key in ('commonnameid','firstnameid','lastnameid')};wanted.discard(None)
    names={r['nameid']:r['name'] for r in matching(base,'playernames',['nameid','name'],'nameid',wanted)}
    names.update({r['nameid']:r['name'] for r in rows('dcplayernames',['nameid','name']) if r['nameid'] in wanted})
    edited={r['playerid']:r for r in rows('editedplayernames',['playerid','firstname','surname','commonname','playerjerseyname']) if r['playerid'] in ids}
    fixture,roster=pack_fixture(club,team['teamname'],team,players,lineup,names,edited)
    result=dict(fixture=fixture,roster=roster,name=team['teamname'],club=club,save_hash=cache.save_hash if cache else hashlib.sha256(raw).hexdigest(),revision=hashlib.sha256(fixture).hexdigest())
    if cache:cache.results[club]=result
    return result
