"""Validated, optional presentation overrides for the globe. Never edit the DB."""
from configparser import ConfigParser, Error
from pathlib import Path
import math,re

RELATIVE='ModCarrerMode/data/club_browser/catalog_overrides.ini'
SCOPES={'national','regional','international','independent'}
FIELDS={
    'club':{'name','country_id','city','state','latitude','longitude','world_id'},
    'country':{'name','world_id','latitude','longitude'},
    'league':{'name','country_id','scope','state','division_label','latitude','longitude'},
}

def load(game):
    result={kind:{} for kind in FIELDS};warnings=[];path=Path(game)/RELATIVE
    if not path.is_file():return result,warnings
    parser=ConfigParser(interpolation=None)
    try:
        with path.open(encoding='utf-8-sig') as handle:parser.read_file(handle)
    except (OSError,UnicodeError,Error) as exc:return result,[str(exc)]
    for section in parser.sections():
        try:
            match=re.fullmatch(r'(club|country|league):([1-9][0-9]*)',section)
            if not match:raise ValueError('use [club:ID], [country:ID] ou [league:ID]')
            kind,ident=match[1],int(match[2]);values=dict(parser.items(section))
            if set(values)-FIELDS[kind]:raise ValueError('campo desconhecido: '+', '.join(sorted(set(values)-FIELDS[kind])))
            if ('latitude' in values)!=('longitude' in values):raise ValueError('latitude e longitude devem ser informadas juntas')
            for key,value in list(values.items()):
                if key in ('country_id','world_id'):
                    values[key]=int(value)
                    if not 0<=values[key]<=(255 if key=='world_id' else 10000):raise ValueError(key+' fora do intervalo')
                elif key in ('latitude','longitude'):
                    values[key]=float(value);limit=90 if key=='latitude' else 180
                    if not math.isfinite(values[key]) or abs(values[key])>limit:raise ValueError(key+' inválida')
                else:
                    if not value.strip() or len(value)>180 or any(c in value for c in '\t\r\n'):raise ValueError(key+' inválido')
                    if key=='scope' and value not in SCOPES:raise ValueError('scope inválido')
            result[kind][ident]=values
        except (ValueError,TypeError) as exc:warnings.append(section+': '+str(exc))
    return result,warnings
