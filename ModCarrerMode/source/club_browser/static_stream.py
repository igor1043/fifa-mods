"""Keep static XI/mascots on the verified player's persistent draw path.

The two frames are byte-identical, so this never animates the authored pose.
Only generated assets are changed; native club models/textures remain read-only.
"""
from pathlib import Path
import json,struct
from rx3 import Rx3,VERTEX
from native_assets import player_coefficient

VERSION=1

def prepare(folder,read_asset):
 folder=Path(folder);meta=json.loads((folder/'assets.json').read_text(encoding='utf8'))
 buffers=Rx3((folder/'geometry.rx3').read_bytes()).get(VERTEX)
 slots=meta.get('used_slots',[])
 if not isinstance(slots,list) or not slots or len(slots)>96 or any(type(slot) is not int for slot in slots) or slots!=sorted(set(slots)):raise ValueError('Malhas estáticas inválidas')
 tracks=[];total=24
 for slot in slots:
  if type(slot) is not int or not 0<=slot<len(buffers):raise ValueError('Slot estático inválido')
  vb=buffers[slot];count,stride=struct.unpack_from('<II',vb,4)
  if not 3<=count<=58000 or stride!=20 or len(vb)<16+count*stride:raise ValueError('Buffer estático incompatível')
  frame=vb[16:16+count*stride];tracks.append((slot,count,frame));total+=8+2*len(frame)
 if total>256*1024*1024:raise ValueError('Cena estática excede o limite de memória')
 # The same native coefficient payload/mips used by the stable player path.
 # A zero-filled coeff map is not equivalent to the original material inputs.
 coefficient=player_coefficient(read_asset('data/sceneassets/prop/prop_102_textures.rx3'))
 with (folder/'animation.bin').open('wb') as file:
  file.write(b'FFPVTX01'+struct.pack('<IIIf',len(tracks),2,0,1.))
  for slot,count,frame in tracks:file.write(struct.pack('<II',slot,count)+frame+frame)
 (folder/'neutral_coeff.rx3').write_bytes(coefficient)
 meta.update(stable_geometry_stream='constant_frames_v1',stable_stream_player=0,
             player_coefficient='native_payload_all_mips_v1')
 (folder/'assets.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 return meta
