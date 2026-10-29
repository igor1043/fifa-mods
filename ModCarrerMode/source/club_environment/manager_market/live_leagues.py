"""Validate the owner-thread publication of all primary league rows in RAM."""
from pathlib import Path
import hashlib,json

FIELDS=('teamid','leagueid','secondarytable','nummatchesplayed','points','homewins','homedraws','homelosses','awaywins','awaydraws','awaylosses','homegf','homega','awaygf','awayga','currenttableposition')

def read(path,observed,now_ms):
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
 if not 0<=now_ms-headers.get('captured_ms',0)<=12000:raise ValueError('Aguardando nova leitura das ligas em RAM')
 if not 0<len(rows)<=8192:raise ValueError('Quantidade inválida de clubes nas ligas')
 revision=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return dict(rows=rows,revision=revision,date=observed['date'],captured_ms=headers['captured_ms'])
