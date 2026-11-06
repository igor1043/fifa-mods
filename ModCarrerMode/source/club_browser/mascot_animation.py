"""Retarget FIFA's standing celebration to the club's own 31-bone mascot.

Only generated private vertex streams change. The model, textures, UVs and
native render resources stay immutable; frame zero is the verified static pose.
"""
from pathlib import Path
import bisect,json,struct
import numpy as np
from rx3 import Rx3,read_model,VERTEX
from player_animation import rotation,slerp,encode
from native_assets import STRIDE

PARENTS=(-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0)
MAX_BYTES=64*1024*1024

def prepare(model,clip_path,folder,cancel=None):
 folder=Path(folder);meta=json.loads((folder/'assets.json').read_text())
 clip=json.loads(Path(clip_path).read_text(encoding='utf-8-sig'))
 parts,raw=read_model(Rx3(model))
 if len(raw)!=31:raise ValueError('Esqueleto do mascote não possui 31 ossos')
 bind=np.asarray(raw,dtype=float).reshape(31,4,4).transpose(0,2,1)
 reference=np.asarray(clip['reference'],dtype=float).reshape(31,7)
 frames=np.asarray(clip['frames'],dtype=float).reshape(-1,31,7);times=clip['times'];duration=float(clip['duration'])
 if frames.shape!=(len(times),31,7) or not 0<duration<=18 or len(times)<2 or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Clipe de comemoração inválido')
 if not np.isfinite(bind).all() or not np.isfinite(frames).all():raise ValueError('Esqueleto não finito')
 ref=np.array([rotation(q) for q in reference[:,3:]])
 inv=np.linalg.inv(bind)
 points=np.concatenate([np.asarray(p['positions']).reshape(-1,3) for p in parts]);low,high=points.min(0),points.max(0)
 centre=np.array([(low[0]+high[0])/2,low[1],(low[2]+high[2])/2])
 chunks=[]
 for part in parts:
  p=np.asarray(part['positions']).reshape(-1,3);n=np.asarray(part['normals']).reshape(-1,3);uv=np.asarray(part['uvs']).reshape(-1,2)
  joints=np.asarray(part['joints'],dtype=int).reshape(-1,4);weights=np.asarray(part['weights'],dtype=float).reshape(-1,4)
  if joints.min()<0 or joints.max()>=31 or np.any(weights.sum(1)<=0):raise ValueError('Pesos do mascote incompatíveis')
  weights/=weights.sum(1)[:,None]
  ids=np.asarray(part['indices'],dtype='<u4')
  for start in range(0,len(ids),54000):
   unique,index=np.unique(ids[start:start+54000],return_inverse=True)
   chunks.append((p[unique],n[unique],uv[unique],joints[unique],weights[unique],index.astype('<u4')))
 plans=[];group=[];count=0
 for chunk in chunks:
  if count+len(chunk[0])>58000:plans.append(group);group=[];count=0
  group.append(chunk);count+=len(chunk[0])
 if group:plans.append(group)
 slots=meta['used_slots']
 if slots!=list(range(len(plans))):raise ValueError('Ordem de malhas da comemoração incompatível')
 buffers=Rx3((folder/'geometry.rx3').read_bytes()).get(VERTEX)
 tracks=[]
 for slot,plan in zip(slots,plans):
  p,n,uv,js,ws=[np.concatenate([c[i] for c in plan]) for i in range(5)]
  idx=[];offset=0
  for c in plan:idx.append(c[5]+offset);offset+=len(c[0])
  initial=buffers[slot][16:16+offset*20]
  v=np.zeros(offset,dtype=STRIDE);v['p']=p-centre;v['n']=n;v['uv']=uv
  # Verify the exact converter plan before publishing an animation.
  if encode(v,np.concatenate(idx))!=initial:raise ValueError('Frame inicial diferente da malha nativa')
  tracks.append((slot,p,n,uv,js,ws,np.concatenate(idx),initial,[]))
 vertices=sum(len(t[1]) for t in tracks);count=min(64,int((MAX_BYTES-24-8*len(tracks))//max(1,20*vertices)))
 if count<12:raise ValueError('Modelo excede o limite da comemoração')
 length=duration+.7
 for frame,time in enumerate(np.linspace(0,length,count)):
  if cancel and cancel():raise InterruptedError('Seleção do mascote alterada')
  if frame in (0,count-1):
   for t in tracks:t[-1].append(t[-2])
   continue
  time=float(time);source=max(0,min(duration,time-.35));hi=min(len(times)-1,max(1,bisect.bisect_right(times,source)));lo=hi-1
  alpha=max(0,min(1,(source-times[lo])/(times[hi]-times[lo])))
  envelope=min(1,time/.35,(length-time)/.35)
  delta=np.array([rotation(slerp(frames[lo,j,3:],frames[hi,j,3:],alpha))@ref[j].T for j in range(31)])
  pose=np.tile(np.eye(4),(31,1,1));pose[:,:3,:3]=delta@bind[:,:3,:3]
  for j,parent in enumerate(PARENTS):pose[j,:3,3]=bind[j,:3,3] if parent<0 or j==2 else pose[parent,:3,3]+delta[parent]@(bind[j,:3,3]-bind[parent,:3,3])
  skin=pose@inv
  for slot,p,n,uv,js,ws,idx,initial,out in tracks:
   moved=np.zeros_like(p);normal=np.zeros_like(n)
   for k in range(4):
    m=skin[js[:,k]];moved+=(np.einsum('nij,nj->ni',m[:,:3,:3],p)+m[:,:3,3])*ws[:,k,None];normal+=np.einsum('nij,nj->ni',m[:,:3,:3],n)*ws[:,k,None]
   v=np.zeros(len(p),dtype=STRIDE);v['p']=p+(moved-p)*envelope-centre;v['n']=n+(normal-n)*envelope;v['n']/=np.maximum(np.linalg.norm(v['n'],axis=1,keepdims=True),1e-8);v['uv']=uv
   if not np.isfinite(v['p']).all() or np.max(np.abs(v['p']))>1000:raise ValueError('Pose do mascote fora do limite')
   out.append(encode(v,idx))
 target=folder/'animation.bin'
 with target.open('wb') as f:
  f.write(struct.pack('<8sIIIf',b'FFPVTX01',len(tracks),count,0,length))
  for slot,p,n,uv,js,ws,idx,initial,out in tracks:f.write(struct.pack('<II',slot,len(p)));f.writelines(out)
 meta.update(celebration=1,animation_frames=count,animation_seconds=length,animation_bytes=target.stat().st_size)
 (folder/'assets.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 return meta
