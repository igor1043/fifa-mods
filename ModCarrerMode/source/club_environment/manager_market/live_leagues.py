"""Validate the owner-thread publication of all primary league rows in RAM."""
from pathlib import Path
import hashlib,json

FIELDS=('teamid','leagueid','secondarytable','nummatchesplayed','points','homewins','homedraws','homelosses','awaywins','awaydraws','awaylosses','homegf','homega','awaygf','awayga','currenttableposition')

def read(path,observed,now_ms,max_age_ms=12000):
 raw=Path(path).read_bytes()
 if len(raw)>4*1024*1024:raise ValueError('Publicação de ligas excede os limites')
 headers={};rows=[];seen=set()
 for line in raw.decode('ascii').splitlines():
  key,value=line.split('=',1)
  if key=='league':
   values=tuple(map(int,value.split(',')))
   if len(values)!=len(FIELDS):raise ValueError('Registro de liga incompleto')
   row=dict(zip(FIELDS,values));identity=(row['teamid'],row['leagueid'],row['secondarytable'])
   if identity in seen or not 0<row['teamid']<=2000000 or not 0<row['leagueid']<1000000 or row['secondarytable']!=0:raise ValueError('Identidade de liga inválida ou duplicada')
   seen.add(identity);rows.append(row)
  else:
   if key in headers:raise ValueError('Cabeçalho duplicado de ligas')
   headers[key]=int(value,16 if key in ('context','registry') else 10)
 save=observed['save'];profile=observed['profile']
 expected=dict(schema=1,complete=1,pid=save['pid'],process_created_100ns=save['process_created_100ns'],club=profile['club_id'],date=observed['date'],context=profile['context_address'],registry=profile['registry_address'],epoch=profile['context_epoch'])
 if any(headers.get(k)!=v for k,v in expected.items()):raise ValueError('Aguardando ligas da sessão e data atuais')
 age=now_ms-headers.get('captured_ms',0)
 if age<0 or (max_age_ms is not None and age>max_age_ms):raise ValueError('Aguardando nova leitura das ligas em RAM')
 if not 0<len(rows)<=8192:raise ValueError('Quantidade inválida de clubes nas ligas')
 rows.sort(key=lambda r:(r['leagueid'],r['teamid'],r['secondarytable']))
 revision=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return dict(rows=rows,revision=revision,date=observed['date'],captured_ms=headers['captured_ms'])


def read_campaign(path,observed):
 raw=Path(path).read_bytes()
 if len(raw)>8*1024*1024:raise ValueError('Campanha diária excede os limites')
 d=json.loads(raw);s=observed['save'];p=observed['profile']
 expected=dict(schema=1,complete=1,pid=s['pid'],created=s['process_created_100ns'],epoch=p['context_epoch'],context=p['context_address'],registry=p['registry_address'],club=p['club_id'],date=observed['date'])
 if any(d.get(k)!=v for k,v in expected.items()):raise ValueError('Campanha de outra sessão ou data')
 nodes=d.get('nodes',[]);standings=d.get('standings',[]);fixtures=d.get('fixtures',[])
 for rows,width in ((nodes,5),(standings,10),(fixtures,11)):
  if not isinstance(rows,list) or len(rows)>65536 or any(len(r)!=width or any(type(v)!=int for v in r) for r in rows):raise ValueError('Campanha diária inválida')
 slots={r[0]:r for r in standings};goals={};overrides={}
 for r in d.get('derivedStandings',[]):
  if len(r)!=14 or any(type(v)!=int or v<0 for v in r) or sum(r[3:9])!=r[9] or max(r[3:9])>255:raise ValueError('Classificação derivada inválida')
  if r[0] in overrides or r[0] not in slots or slots[r[0]][1:3]!=r[1:3]:raise ValueError('Classificação de outra competição')
  overrides[r[0]]=r[:10];goals[str(r[0])]=r[10:]
 return dict(date=d['date'],nodes=nodes,standings=[overrides.get(r[0],r) for r in standings],fixtures=fixtures,standingGoals=goals)
