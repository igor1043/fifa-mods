"""Bounded decoder for the offline eight-influence FIFA rig format."""
from pathlib import Path
import struct
import numpy as np

def read_rig(path):
 data=Path(path).read_bytes();offset=0
 def take(n):
  nonlocal offset
  if n<0 or offset+n>len(data):raise ValueError('Truncated rig')
  value=data[offset:offset+n];offset+=n;return value
 def unpack(fmt):return struct.unpack('<'+fmt,take(struct.calcsize('<'+fmt)))
 def text():
  size,=unpack('I')
  if size>4096:raise ValueError('Invalid text')
  return take(size).decode('utf8')
 if take(8)!=b'FF3D0003':raise ValueError('Unsupported rig')
 count,ntex,nbones,player,height=unpack('5I');name=text()
 if not 1<=count<=256 or not 1<=nbones<=1024 or ntex>512:raise ValueError('Invalid catalog')
 bones=[]
 for _ in range(nbones):
  label=text();parent,=unpack('i');matrix=np.array(unpack('16f')).reshape(4,4).T
  if not -1<=parent<len(bones):raise ValueError('Invalid skeleton order')
  bones.append(dict(name=label,parent=parent,inverse=matrix,rest=np.linalg.inv(matrix)))
 parts=[]
 dtype=np.dtype([('p','<f4',3),('n','<f4',3),('uv','<f4',2),('j','<u2',8),('w','u1',8)])
 for _ in range(count):
  label,asset=text(),text();texture,skinned,blend=unpack('iII');alpha,coeff,*colors=unpack('fi6f');nv,ni=unpack('II')
  if not 0<nv<=5000000 or not 0<ni<=15000000 or ni%3:raise ValueError('Invalid geometry')
  vertices=np.frombuffer(take(nv*dtype.itemsize),dtype=dtype).copy();indices=np.frombuffer(take(ni*4),dtype='<u4').copy()
  if indices.max()>=nv:raise ValueError('Invalid triangle')
  if not np.isfinite(vertices['p']).all() or (vertices['w'].sum(axis=1)==0).any():raise ValueError('Invalid skin')
  if vertices['j'][vertices['w']>0].max()>=nbones:raise ValueError('Invalid bone')
  parts.append(dict(name=label,asset=asset,texture=texture,skinned=skinned,blend=blend,alpha=alpha,coeff=coeff,color=colors[:3],tint=colors[3:],v=vertices,idx=indices))
 textures=[]
 for _ in range(ntex):
  w,h,kind,size=unpack('4I');expected=w*h*4 if kind==3 else ((w+3)//4)*((h+3)//4)*(8 if kind==0 else 16)
  if not 0<w<=4096 or not 0<h<=4096 or not 0<=kind<=3 or size!=expected:raise ValueError('Invalid texture')
  textures.append((w,h,kind,take(size)))
 if offset!=len(data):raise ValueError('Unknown extension')
 return dict(id=player,name=name,height=height,bones=bones,parts=parts,textures=textures)

def skin(rig,pose):
 matrices=np.array(pose).reshape(-1,4,4).transpose(0,2,1)
 delta=matrices@np.array([b['inverse'] for b in rig['bones']]);result=[]
 for part in rig['parts']:
  v=part['v'];p=np.c_[v['p'],np.ones(len(v))];out=np.zeros((len(v),3));weights=v['w']/v['w'].sum(axis=1)[:,None]
  for i in range(8):out+=(delta[v['j'][:,i],:3,:]@p[:,:,None])[:,:,0]*weights[:,i,None]
  result.append(out)
 return result
