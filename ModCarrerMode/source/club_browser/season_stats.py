"""Player season totals from the existing verified native career publication."""
from pathlib import Path
from datetime import datetime,date
import json,struct

def current(game,memory,saved,profile):
 try:
  path=Path(game)/'ModCarrerMode/runtime/career_fce_snapshot.json'
  if path.stat().st_size>32*1024*1024:return None
  s=json.loads(path.read_text(encoding='utf8'))
  if s.get('schema')!=3 or s.get('pid')!=memory.process_id or s.get('club')!=profile['club_id']:return None
  if s.get('processCreated100ns')!=saved['process_created_100ns'] or Path(s['savePath']).resolve()!=Path(saved['path']).resolve() or s.get('saveSize')!=saved['size'] or s.get('saveWriteTime100ns')!=saved['mtime_ns']//100+116444736000000000:return None
  code=memory.read_process_memory(memory.base_module+0x44563f0,24)
  if code[7:9]!=b'\xc7\x01':return None
  index=struct.unpack_from('<I',code,9)[0]
  if not 0<=index<256:return None
  calendar=memory.read_int64(memory.read_int64(profile['registry_address']+index*32+24));d,m,y=struct.unpack('<3i',memory.read_process_memory(calendar+0x34,12));today=y*10000+m*100+d
  datetime.strptime(str(today),'%Y%m%d')
  return s if s.get('date')==today else None
 except (OSError,ValueError,KeyError,TypeError,struct.error):return None

def totals(snapshot,club):
 if not snapshot:return {}
 nodes={r[0]:r for r in snapshot.get('nodes',[]) if len(r)==5};cache={}
 def root(identifier):
  if identifier in cache:return cache[identifier]
  node=identifier;seen=set()
  while node in nodes and node not in seen:
   seen.add(node);record=nodes[node]
   if record[2]==3:cache[identifier]=node;return node
   node=record[1]
  raise ValueError('Unresolved competition')
 records={};groups={}
 for row in snapshot.get('stats',[]):
  if len(row)<8 or row[2]!=club:continue
  if any(type(v)!=int for v in row[:8]) or min(row[3:8])<0:raise ValueError('Invalid native statistics')
  key=(row[1],row[3]);value=tuple(row[4:8])
  if key in records and records[key]!=value:raise ValueError('Conflicting native statistics')
  records[key]=value
 for (phase,player),values in records.items():groups.setdefault((root(phase),player),{})[phase]=values
 result={}
 for (competition,player),phases in groups.items():
  values=phases[competition] if competition in phases else tuple(map(sum,zip(*phases.values())))
  previous=result.get(player,(0,0,0,0));result[player]=tuple(a+b for a,b in zip(previous,values))
 return result

def age(birth,today):
 try:
  from datetime import timedelta
  born=date(1582,10,14)+timedelta(days=birth);at=datetime.strptime(str(today),'%Y%m%d').date();value=at.year-born.year-((at.month,at.day)<(born.month,born.day))
  return value if 14<=value<=65 else -1
 except (TypeError,ValueError,OverflowError):return -1
