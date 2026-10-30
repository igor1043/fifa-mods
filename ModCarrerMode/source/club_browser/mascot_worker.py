"""Read the career club's own mascot package; publish a static native viewer."""
from pathlib import Path
import base64,hashlib,json,os,shutil,struct,tempfile
import numpy as np
import portable_paths
from rx3 import Rx3,read_model,diffuse
from native_assets import convert,STRIDE
from character_lighting import ensure
from lineup_worker import observe,request,publish,atomic
from static_stream import prepare as prepare_static

VERSION=1

def package(game,club):
 if type(club) is not int or not 0<club<500000:raise ValueError('Clube inválido')
 root=Path(game)/'data/sceneassets/mascot'/str(club)
 paths=[root/'model.rx3',root/'textures.rx3']
 return paths if all(p.is_file() for p in paths) else None

def model_bytes(model,texture):
 """Keep authored geometry/UVs/colour pixels, only centre it on the pitch."""
 parts,_=read_model(Rx3(model));_,image=diffuse(Rx3(texture))
 all_points=np.concatenate([np.asarray(p['positions'],dtype='f4').reshape(-1,3) for p in parts])
 low,high=all_points.min(axis=0),all_points.max(axis=0);height=float(high[1]-low[1])
 if not 20<=height<=500:raise ValueError('Dimensões do mascote incompatíveis')
 centre=np.array([(low[0]+high[0])/2,low[1],(low[2]+high[2])/2],dtype='f4')
 encoded=[]
 for part in parts:
  v=np.zeros(len(part['positions'])//3,dtype=STRIDE)
  v['p']=np.asarray(part['positions'],dtype='f4').reshape(-1,3)-centre
  v['n']=np.asarray(part['normals'],dtype='f4').reshape(-1,3);v['uv']=np.asarray(part['uvs'],dtype='f4').reshape(-1,2)
  ids=np.asarray(part['indices'],dtype='<u4')
  # Bound each native submesh to the converter's 16-bit index range.
  for start in range(0,len(ids),54000):
   selected=ids[start:start+54000];unique,inverse=np.unique(selected,return_inverse=True)
   encoded.append(struct.pack('<IIii7f',len(unique),len(selected),0,0,1.,1.,1.,1.,1.,1.,1.)+v[unique].tobytes()+inverse.astype('<u4').tobytes())
 if not encoded or len(encoded)>512:raise ValueError('Malhas do mascote incompatíveis')
 pixels=base64.b64decode(image['data']);w,h,kind=image['width'],image['height'],image['format']
 return b'FF3D0001'+struct.pack('<II',len(encoded),1)+b''.join(encoded)+struct.pack('<4I',w,h,kind,len(pixels))+pixels,height

def generate(game,folder,req,memory,projection_cache=None):
 saved,context=observe(memory,game)
 def current():
  after,ctx=observe(memory,game)
  return request(folder/'request.tsv',req['pid'])==req and ctx==context and after['path'].casefold()==saved['path'].casefold() and (after['size'],after['mtime_ns'])==(saved['size'],saved['mtime_ns'])
 def ready(**values):
  if not current():return False
  publish(folder,req,'ready',kind='mascot',career=context[2],**values);return True
 paths=package(game,req['club'])
 if paths is None:return ready(actor=0)
 model,texture=[p.read_bytes() for p in paths]
 identity=hashlib.sha256(b'mascot-viewer-v2-stable-stream\0'+str(req['club']).encode()+model+texture).hexdigest()
 cache=Path(game)/'ModCarrerMode/cache/club_browser/mascot'/identity
 target=Path(game)/'data/sceneassets/server16_club_xi'/str(req['pid'])/identity
 ensure(game,portable_paths.read_asset)
 if not (cache/'assets.json').is_file():
  with tempfile.TemporaryDirectory(prefix='mascot-',dir=folder) as temp:
   temp=Path(temp);blob,_=model_bytes(model,texture);(temp/'mascot.ff3d').write_bytes(blob)
   convert(temp/'mascot.ff3d',temp/'native',portable_paths.read_asset,Path(game)/'ModCarrerMode/cache/club_browser/xi/materials')
   prepare_static(temp/'native',portable_paths.read_asset)
   if not current():return False
   cache.parent.mkdir(parents=True,exist_ok=True);os.replace(temp/'native',cache)
 if not current():return False
 if not (target/'assets.json').is_file():
  target.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='mascot-publish-',dir=target.parent) as temp:
   out=Path(temp)/'native';out.mkdir()
   for item in cache.iterdir():
    try:os.link(item,out/item.name)
    except OSError:shutil.copy2(item,out/item.name)
   os.replace(out,target)
 assets=json.loads((target/'assets.json').read_text());bounds=assets['bounds']
 return ready(actor=1,hash=identity,height=round(bounds[4]-bounds[1]),pages=assets['pages'],
              bindings=','.join(str(row[0]) for row in assets['bindings']),renderer='native',stable_stream=1)
