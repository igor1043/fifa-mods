"""Decode competition counters from the validated career file, never RAM."""
import struct
from competition_schedule import read_schedule

def read(raw,today):
 marker=raw.find(b'FCE_Setup_Stage');offset=marker-106
 if marker<0 or offset<0:raise ValueError('Estrutura FCE do save não encontrada')
 blocks=[]
 for stride in (47,10,21,12,20,10,14,21):
  rows=[]
  while offset+stride<=len(raw) and len(rows)<65536 and struct.unpack_from('<H',raw,offset)[0]==len(rows):
   rows.append(raw[offset:offset+stride]);offset+=stride
  if not rows:raise ValueError('Bloco FCE incompleto no save')
  blocks.append(rows)
 if len(blocks[0])<3 or blocks[0][0][12:16]!=b'FIFA':raise ValueError('Cabeçalho FCE inválido')
 nodes=[]
 for r in blocks[0]:
  if r[2]!=1:continue
  key=r[6:12].split(b'\0',1)[0].decode('ascii',errors='ignore')
  title=r[12:45].split(b'\0',1)[0].decode('ascii',errors='ignore')
  text=title.removeprefix('TrophyName_Abbr15_') if title.startswith('TrophyName_Abbr15_') else key[1:] if key.startswith('C') else ''
  nodes.append([struct.unpack_from('<H',r,3)[0],struct.unpack_from('<h',r,45)[0],r[5],int(text) if text.isdigit() else -1,0])
 standings=[];goals={}
 for r in blocks[7]:
  if r[2]!=1:continue
  team=struct.unpack_from('<i',r,5)[0]
  if team<0:continue
  # +9 is seed/rank, not wins. Home and away each serialize five bytes.
  wdl=[r[i] for i in (10,11,12,15,16,17)]
  standings.append([struct.unpack_from('<H',r)[0],struct.unpack_from('<H',r,3)[0],team,*wdl,sum(wdl)])
  goals[str(struct.unpack_from('<H',r)[0])]=[r[i] for i in (13,14,18,19)]
 fixtures=[]
 for m in read_schedule(raw):
  fixtures.append([m['id'],m['group'] if m['group'] is not None else m['stage'],m['stage'],m['date'],int(m['time'].replace(':','')),m['home'],m['away'],m['homeScore'] if m['homeScore'] is not None else 255,m['awayScore'] if m['awayScore'] is not None else 255,int(m['played'])])
 return dict(date=today,nodes=nodes,standings=standings,standingGoals=goals,fixtures=fixtures,stats=[],source='career_file')
