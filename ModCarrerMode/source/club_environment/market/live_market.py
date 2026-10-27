"""Validate complete owner-thread snapshots of the currently open career."""
import hashlib,json
from pathlib import Path

OFFER_FIELDS=('offerid','result','offeredfee','teamid','offerteamid','snipedteamid','playerid','exchangeplayerid','date','stage','iscputransfer','isloan','isloanbuy','issnipe')
CONTRACT_FIELDS=('offerid','teamid','offerteamid','playerid','date','completedate','iscputransfer')
PLAYER_FIELDS=('playerid','commonnameid','firstnameid','lastnameid','overallrating','potential','preferredposition1')
TABLES={'offer':('offers',OFFER_FIELDS),'precontract':('precontracts',CONTRACT_FIELDS),'player':('players',PLAYER_FIELDS),'link':('links',('playerid','teamid'))}

def read_live(path,snapshot,now_ms):
    fields={};tables={key:[] for key,_ in TABLES.values()}
    raw=Path(path).read_bytes()
    if len(raw)>8*1024*1024:raise ValueError('Snapshot do mercado excede o limite de leitura.')
    for line in raw.decode('ascii').splitlines():
        key,value=line.split('=',1)
        if key in TABLES:
            name,columns=TABLES[key];values=tuple(map(int,value.split(',')))
            if len(values)!=len(columns):raise ValueError('Linha incompleta do mercado.')
            tables[name].append(dict(zip(columns,values)))
        else:
            if key in fields:raise ValueError('Cabeçalho duplicado do mercado.')
            fields[key]=int(value,16 if key in ('registry','context') else 10)
    profile=snapshot['profile'];save=snapshot['save']
    expected=dict(schema=1,complete=1,pid=save['pid'],club=profile['club_id'],date=snapshot['date'],
        context=profile['context_address'],registry=profile['registry_address'],epoch=profile['context_epoch'])
    if any(fields.get(key)!=value for key,value in expected.items()):raise ValueError('Aguardando os negócios da carreira atual.')
    if not 0<=now_ms-fields.get('captured_ms',0)<=12000:raise ValueError('Aguardando nova leitura do mercado na RAM.')
    if any(len(rows)>16384 for rows in tables.values()):raise ValueError('Quantidade de negócios fora dos limites.')
    # Exclude capture time: an unchanged market must not rebuild/reload the UI.
    revision=hashlib.sha256(json.dumps(tables,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(**tables,revision=revision,capturedMs=fields['captured_ms'],entry=fields['entry'],source='live-career')
