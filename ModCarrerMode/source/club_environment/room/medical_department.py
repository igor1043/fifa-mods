"""Optional complete clinical pack; native career files always remain read-only."""
from pathlib import Path
from functools import lru_cache
import copy,hashlib,json,os
import numpy as np
from PIL import Image

PREFIX='data/sceneassets/server16_dressing_room_v3/medical_department/'
MANIFEST=PREFIX+'clinic.json'


def stamp(game):
 p=Path(game)/MANIFEST
 return (str(p),p.stat().st_mtime_ns,p.stat().st_size) if p.is_file() else None


@lru_cache(maxsize=4)
def _read(file,modified,size):return json.loads(Path(file).read_text(encoding='utf8'))


def specification(game):
 key=stamp(game)
 if key is None:return None
 spec=_read(*key)
 return spec if spec.get('schema')==1 and all((Path(game)/p).is_file() for p in spec['required']) else None


def translated(identity,position):
 m=np.array(identity,dtype=float).reshape(4,4).T.copy();m[:3,3]+=position
 return m.T.reshape(-1).tolist()


def prepare(game,context,read_asset,add,identity):
 spec=specification(game)
 if not spec:return False
 from medical_department_art import injury_board,summary_board,followup_board,identity_wall,door_sign
 from room_v3 import texture
 materials=dict(spec['materials']);images={'summary':summary_board(context),'followup':followup_board(context),'identity':identity_wall(context,read_asset),
  'door_medical':door_sign(context,read_asset,'medical'),'door_coach':door_sign(context,read_asset,'coach')}
 for binding in spec['bindings']:
  material=binding['material'];key='medical_clinical_'+binding['batch']
  if material=='board_injuries':
   pages=context['medical']['pages']
   for page in range(pages):
    tex=texture(game,injury_board(context,read_asset,page),'medical_injuries',mipmaps=False)
    add(key+'_'+str(page),spec['model'],tex,'v3_cm',identity,submesh=binding['submesh'],page=page,pages=pages,bank=0)
   continue
  if material.startswith('board_'):
   board=material[6:]
   tex=spec['posters'][board] if board in spec['posters'] else texture(game,images[board],'medical_'+board,mipmaps=False)
   texname='medical_cm' if board in spec['posters'] else 'v3_cm'
  else:tex=materials[material];texname='medical_cm'
  add(key,spec['model'],tex,texname,identity,submesh=binding['submesh'])
 for asset in spec['cardio']:
  for binding in asset['bindings']:
   for position in asset['positions']:
    add('medical_'+asset['name']+'_'+binding['batch'],asset['model'],materials[binding['material']],'medical_cm',translated(identity,position),submesh=binding['submesh'])
 for binding in spec['imported']:
  if binding['hydration']:
   kind='bottle' if 'bottle_' in binding['key'] else 'cooler'
   positions=spec['hydration'][kind+'_positions']
  else:positions=[[0,0,0]]
  for position in positions:add(binding['key'],binding['model'],binding['texture'],binding['texname'],translated(identity,position),binding['alpha'],submesh=binding['submesh'])
 for binding in spec['office']:add(binding['key'],binding['model'],binding['texture'],binding['texname'],identity,binding['alpha'],submesh=binding['submesh'])
 context['medical']['environment']='clinical_department_1'
 return True


def layout(game,original):
 spec=specification(game)
 if not spec:return original
 result=copy.deepcopy(original);medical=result['medical'];medical['room_bounds']=spec['bounds']
 for row in medical['scenes']:
  if row['label'].startswith('Departamento médico · '):
   key=row['label'].split(' · ',1)[1]
   if key in spec['scenes']:row['pose']=spec['scenes'][key]
 # Retain the coach navigation and the unchanged shared door approaches.
 medical['navigation']=[p for p in medical.get('navigation',[]) if p[0]>-335 or p[2]<1750]
 medical['navigation'] += [[x,180,z,x,180,z+100,65] for x,z in ((-1000,1750),(-1050,2110),(-1030,2420),(-1040,2710),(-600,1890),(-430,2240))]
 return result


def obstacles(game,items):
 spec=specification(game)
 if not spec:return items
 return [p for p in items if not p['name'].startswith(('Departamento médico R77 / ','Reabilitação / ','Medical department / '))]+copy.deepcopy(spec['obstacles'])


def outside_clinic(vertices,indices):
 """Clip the west annex only; preserve main room and coach vertices/UVs."""
 from room_visual_r68 import VERT,box
 v=vertices.copy();v['p'][:,0]*=-1;added=[];kept=[];count=len(v)
 def split(poly,axis,bound):
  inside=[];outside=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   av=float(a['p'][axis]-bound);bv=float(b['p'][axis]-bound)
   (inside if av>=0 else outside).append(a)
   if (av<0)!=(bv<0):
    t=av/(av-bv);p=a.copy();p['p']=a['p']+(b['p']-a['p'])*t;p['uv']=a['uv'].astype(float)+(b['uv'].astype(float)-a['uv'].astype(float))*t;inside.append(p);outside.append(p.copy())
  return inside,outside
 def append(poly):
  nonlocal count
  for i in range(1,len(poly)-1):
   tri=[poly[0],poly[i],poly[i+1]];p=np.array([a['p'] for a in tri])
   if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<.0001:continue
   added.extend(tri);kept.extend((count,count+1,count+2));count+=3
 for tri in indices.reshape(-1,3):
  p=v['p'][tri]
  if p[:,0].max()<335 or p[:,2].max()<1555:kept.extend(tri);continue
  if p[:,0].min()>=335 and p[:,2].min()>=1555:continue
  inside,outside=split([v[i].copy() for i in tri],0,335);append(outside)
  if inside:_,outside=split(inside,2,1555);append(outside)
 if not kept:return box((0,900,0),(.1,900.1,.1))
 v=np.concatenate([v,np.array(added,dtype=VERT)]) if added else v;used,inverse=np.unique(kept,return_inverse=True);v=v[used].copy();v['p'][:,0]*=-1
 if len(v)>=65536:raise ValueError('Clinical clipping exceeds the native vertex budget')
 return v,inverse.reshape(-1).astype('<u2')


def old_hydration(vertices,indices):
 p=vertices['p'][indices.reshape(-1,3)]
 coolers=((p>=[548,1094,1477])&(p<=[651,1142,1532])).all((1,2))
 bottles=((p>=[344,1094,1498])&(p<=[436,1128,1512])).all((1,2))
 return coolers|bottles


def model_path(game,model):
 spec=specification(game)
 if not spec or model.startswith(PREFIX):return model
 stem=Path(model).stem
 if not model.startswith('data/sceneassets/server16_dressing_room_v3/') or not stem.startswith(('interior','room_roles','scenery','crest_surfaces','floor_shadows')):return model
 p=Path(game)/model;stat=p.stat()
 return _model(str(Path(game).resolve()),model,stat.st_mtime_ns,stat.st_size,spec['root'])


@lru_cache(maxsize=16)
def _model(game,model,modified,size,revision):
 from rx3 import Rx3,VERTEX
 from room_visual_r68 import read_mesh,replace_mesh,box
 game=Path(game);rx=Rx3((game/model).read_bytes());changed=False
 for slot in range(len(rx.get(VERTEX))):
  v,ids=read_mesh(rx,slot);a,b=outside_clinic(v,ids)
  if Path(model).stem.startswith('interior'):
   tri=b.reshape(-1,3);keep=~old_hydration(a,b)
   if not keep.all():
    if keep.any():used,inverse=np.unique(tri[keep],return_inverse=True);a,b=a[used],inverse.reshape(-1).astype('<u2')
    else:a,b=box((0,900,0),(.1,900.1,.1))
  if a.tobytes()!=v.tobytes() or b.tobytes()!=ids.tobytes():replace_mesh(rx,slot,a,b);changed=True
 if not changed:return model
 payload=rx.build();name=PREFIX+'variants/'+Path(model).stem+'_'+hashlib.sha256(payload).hexdigest()[:14]+'.rx3';p=game/name
 if not p.is_file():
  p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.'+str(os.getpid())+'.new');tmp.write_bytes(payload);os.replace(tmp,p)
 return name
