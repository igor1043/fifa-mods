"""Build the market snapshot from the native DATA bytes; never opens a writer."""
from pathlib import Path
from threading import RLock
from functools import lru_cache
import hashlib,json,struct,xml.etree.ElementTree as ET,zlib
from fifa_db import FifaDatabase
import market_projection as projection
_projection_lock=RLock()

def blocks(raw):
    if len(raw)<180 or struct.unpack_from('<I',raw,136)[0]!=56 or struct.unpack_from('<I',raw,132)[0]!=zlib.crc32(raw[160:]):
        raise ValueError('O save não passou na verificação de integridade.')
    found=[];at=160
    while True:
        at=raw.find(b'DB\0\x08',at)
        if at<0:break
        size=struct.unpack_from('<I',raw,at+8)[0];count=struct.unpack_from('<I',raw,at+16)[0]
        if 24<=size<=len(raw)-at and 0<count<512:found.append((at,size));at+=size
        else:at+=4
    if len(found)!=3:raise ValueError('Esperados três bancos no save da carreira.')
    return found

class Snapshot(projection.MarketProjection):
    def refresh(self):pass

class CachedCatalog(FifaDatabase):
    def rows(self,name,fields):
        if not hasattr(self,'_row_cache'):self._row_cache={}
        key=(name,tuple(fields))
        if key not in self._row_cache:self._row_cache[key]=super().rows(name,fields)
        return self._row_cache[key]

@lru_cache(maxsize=2)
def _catalog(game,stamp):return CachedCatalog(game,include_all_tables=True)

def read_snapshot(game,save,*,club_override=None,date_override=None,live=None):
    game=Path(game);save=Path(save);raw=save.read_bytes();before=hashlib.sha256(raw).hexdigest()
    databases=[FifaDatabase(game,raw[at:at+size],include_all_tables=True) for at,size in blocks(raw)]
    roster=next(db for db in databases if {'teams','players','teamplayerlinks'}<=db.tables.keys())
    def rows(name,fields):
        matches=[db for db in databases if name in db.tables]
        if len(matches)>1:raise ValueError('Tabela ambígua no save: '+name)
        return matches[0].rows(name,fields) if matches else []
    catalogue=game/'data/db/fifa_ng_db.db';meta=game/'data/db/fifa_ng_db-meta.xml'
    base=_catalog(str(game),(catalogue.stat().st_size,catalogue.stat().st_mtime_ns,meta.stat().st_mtime_ns))
    teams={r['teamid']:r['teamname'] for r in base.rows('teams',['teamid','teamname'])}
    teams.update({r['teamid']:r['teamname'] for r in roster.rows('teams',['teamid','teamname']) if r.get('teamname')})
    leagues={r['leagueid']:r for r in base.rows('leagues',['leagueid','leaguename','level'])}
    # Career league names can be unused FF-filled placeholders. Keep the real
    # installed names, while deriving club membership from the saved links.
    links=roster.rows('leagueteamlinks',['teamid','leagueid','secondarytable']) if 'leagueteamlinks' in roster.tables else base.rows('leagueteamlinks',['teamid','leagueid','secondarytable'])
    memberships={r['teamid']:r['leagueid'] for r in links if r.get('secondarytable')==0 and leagues.get(r['leagueid'],{}).get('level',0)>0}
    catalog=[dict(id=ident,name=name,leagueId=memberships.get(ident),leagueName=leagues.get(memberships.get(ident),{}).get('leaguename','Liga não identificada'),leagueIcon='',crest='') for ident,name in teams.items()]
    users=rows('career_users',['userid','clubteamid','firstname','surname'])
    if len(users)!=1:raise ValueError('Não foi possível identificar um único clube de treinador no save.')
    club=users[0]['clubteamid'] if club_override is None else int(club_override)
    if club not in teams:raise ValueError('O clube atual não existe na base desta carreira.')
    calendar_db=next(db for db in databases if 'career_calendar' in db.tables)
    definitions=next(t for t in ET.parse(game/'data/db/fifa_ng_db-meta.xml').getroot().iter('table') if t.get('name')=='career_calendar')
    fields={f.get('shortname'):f for f in definitions.iter('field')}
    date_row=calendar_db.rows('career_calendar',['currdate'])
    if len(date_row)!=1:raise ValueError('Data da carreira ambígua.')
    saved_date=date_row[0]['currdate']
    calendar=dict(careerDate=saved_date if date_override is None else int(date_override))
    if projection.MarketProjection._career_date(calendar['careerDate']) is None or calendar['careerDate']<saved_date:
        raise ValueError('Aguardando a data da carreira terminar de carregar.')
    for key,short in dict(windowStart1='sUgA',windowEnd1='PpdA',windowStart2='Jdde',windowEnd2='igYC').items():
        field=fields.get(short)
        if field is not None and field.get('name') in calendar_db.tables['career_calendar']['fields']:
            value=calendar_db.rows('career_calendar',[field.get('name')])[0][field.get('name')]
            calendar[key]=value+(101 if int(field.get('rangelow','0'))==0 else 0)
    calendar['windowEndsValid']=all(calendar.get(k,0)>0 for k in ('windowStart1','windowEnd1','windowStart2','windowEnd2'))
    class LiveRoster:
        def __init__(self,original):self.original=original;self.tables=original.tables
        def rows(self,name,fields):
            replacements={'players':'players','teamplayerlinks':'links'}
            if name in replacements:return [{key:row.get(key) for key in fields} for row in live[replacements[name]]]
            return self.original.rows(name,fields)
    source=Snapshot();source.lock=RLock();source.db=LiveRoster(roster) if live is not None else roster;source.base=base;source.tag=before;source.calendar=calendar
    source.managers={club:dict(clubteamid=club)};source.transfer_market_cache=None
    source.transfer_offers=rows('career_transferoffer',['offerid','result','offeredfee','teamid','offerteamid','snipedteamid','playerid','exchangeplayerid','date','stage','iscputransfer','isloan','isloanbuy','issnipe'])
    source.precontracts=rows('career_precontract',['offerid','teamid','offerteamid','playerid','date','completedate','iscputransfer'])
    if live is not None:
        source.transfer_offers=live['offers'];source.precontracts=live['precontracts'];source.tag=live['revision']
    # The reference's aggregation is reused; membership comes from this save,
    # including promotions/relegations, instead of its static club catalogue.
    with _projection_lock:
        projection.club_catalog=lambda:catalog
        result=source.transfer_market(club)
    result.update(clubName=teams.get(club,'Clube da carreira'),saveFile=str(save),saveSlot=save.parent.name,
        source='live-career' if live is not None else 'native-save',sourceHash=before,readOnly=True,savedDate=saved_date,
        evidence=dict(offersRead=len(source.transfer_offers),precontractsRead=len(source.precontracts),resultRequired=32,destinationRosterVerified=True))
    if live is not None:result.update(liveRevision=live['revision'],capturedMs=live['capturedMs'])
    if hashlib.sha256(save.read_bytes()).hexdigest()!=before:raise ValueError('O save mudou durante a leitura; tente atualizar novamente.')
    return result

def active_save(game):
    record=Path(game)/'ModCarrerMode/runtime/career_active_save.tsv'
    fields=dict(line.split('=',1) for line in record.read_text(encoding='utf-8-sig').splitlines() if '=' in line)
    if fields.get('complete_file')!='1' or fields.get('save_type')!='SaveType_Career':raise ValueError('Nenhum save completo de carreira identificado.')
    return Path(fields['path'].removeprefix('\\\\?\\'))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--save',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=read_snapshot(a.game,a.save or active_save(a.game));a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(club=result['clubName'],date=result['careerDate'],deals=result['summary']['completedDeals'],leagues=len(result['leagues']),evidence=result['evidence']),ensure_ascii=False))
