"""Bake FIFA's own idle clip into native prop vertex streams (no WebGL)."""
from pathlib import Path
import bisect,json,math,struct,collections
import numpy as np
from rig_model import read_rig
from native_assets import STRIDE,read_model,convert,packed
from rx3 import Rx3,VERTEX

def unit(q):
 q=np.asarray(q,dtype=float);n=np.linalg.norm(q)
 if not np.isfinite(q).all() or not .00001<n<10:raise ValueError('Rotação inválida no clipe.')
 return q/n

def mul(a,b):
 x,y,z,w=a;X,Y,Z,W=b
 return np.array([w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z])

def inverse(q):return np.asarray(q)*[-1,-1,-1,1]
def rotation(q):
 x,y,z,w=unit(q)
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def decompose(m):
 s=np.linalg.norm(m[:3,:3],axis=0)
 if np.min(s)<1e-8:raise ValueError('Escala inválida no esqueleto.')
 if np.linalg.det(m[:3,:3])<0:s[0]*=-1
 r=m[:3,:3]/s[None,:];tr=np.trace(r)
 if tr>0:
  n=math.sqrt(tr+1)*2;q=[(r[2,1]-r[1,2])/n,(r[0,2]-r[2,0])/n,(r[1,0]-r[0,1])/n,n/4]
 else:
  i=int(np.diag(r).argmax());j=(i+1)%3;k=(i+2)%3;n=math.sqrt(max(1e-10,1+r[i,i]-r[j,j]-r[k,k]))*2;q=[0.,0.,0.,0.];q[i]=n/4;q[j]=(r[j,i]+r[i,j])/n;q[k]=(r[k,i]+r[i,k])/n;q[3]=(r[k,j]-r[j,k])/n
 return m[:3,3].copy(),unit(q),s

def slerp(a,b,t):
 a,b=unit(a),unit(b);dot=float(np.dot(a,b))
 if dot<0:b=-b;dot=-dot
 if dot>.9995:return unit(a+(b-a)*t)
 angle=math.acos(max(-1,min(1,dot)));return (a*math.sin((1-t)*angle)+b*math.sin(t*angle))/math.sin(angle)

class Animation:
 def __init__(self,rig,clip):
  self.rig=rig;self.clip=clip;self.by_name={b['name']:i for i,b in enumerate(rig['bones'])};self.rest=[]
  for bone in rig['bones']:
   m=bone['rest'] if bone['parent']<0 else rig['bones'][bone['parent']]['inverse']@bone['rest'];self.rest.append(decompose(m))
  self.times=clip['times'];self.frames=clip['frames'];self.channels=clip['channels'];self.duration=float(clip['duration'])
  if not 1<=len(self.times)<=2000 or len(self.frames)!=len(self.times) or not 0<self.duration<=20 or any(b<a for a,b in zip(self.times,self.times[1:])):raise ValueError('Clipe inválido.')
  if any(len(f)!=len(self.channels) for f in self.frames):raise ValueError('Canais incompletos.')
  hips=self.by_name['Hips'];self.basis=mul(self.rest[hips][1],inverse(unit(clip['defaults']['Hips.q'])));default=clip['defaults'].get('Hips.t',[0,0,0])[1]
  self.scale=self.rest[hips][0][1]/default if abs(default)>1e-8 else 30.48
  self.base_local=[]
  for p,q,scale in self.rest:
   matrix=np.eye(4);matrix[:3,:3]=rotation(q)*scale[None,:];matrix[:3,3]=p;self.base_local.append(matrix)
  self.base_local=np.array(self.base_local)
  self.tracks=[]
  for index,name in enumerate(self.channels):
   bone,prop=name.rsplit('.',1)
   if bone not in self.by_name or prop not in ('t','q'):continue
   ref=self.frames[0][index] if prop=='t' and clip.get('translationMode')=='relative' else clip.get('defaults',{}).get(name)
   self.tracks.append((index,bone,self.by_name[bone],prop,ref))
 def pose(self,time):
  hi=min(len(self.times)-1,max(1,bisect.bisect_right(self.times,time)));lo=max(0,hi-1);span=self.times[hi]-self.times[lo];alpha=(time-self.times[lo])/span if span>0 else 0;alpha=max(0,min(1,alpha));local=[[p.copy(),q.copy(),s.copy()] for p,q,s in self.rest]
  for index,name,bone,prop,ref in self.tracks:
   a,b=self.frames[lo][index],self.frames[hi][index]
   if prop=='q':
    q=slerp(a,b,alpha)
    if name=='Hips':q=mul(self.basis,q)
    elif name=='AITrajectory':q=mul(mul(self.basis,q),inverse(self.basis))
    local[bone][1]=q
   else:
    v=np.array(a[:3],dtype=float)+(np.array(b[:3],dtype=float)-a[:3])*alpha
    if ref is not None:v-=ref[:3]
    if name in ('Hips','AITrajectory'):v=rotation(self.basis)@v
    local[bone][0]+=v*self.scale
  if 'AITrajectory' in self.by_name:
   i=self.by_name['AITrajectory'];local[i][0][[0,2]]=self.rest[i][0][[0,2]]
  matrices=self.base_local.copy()
  for i in {track[2] for track in self.tracks}:
   p,q,scale=local[i];matrices[i,:3,:3]=rotation(q)*scale[None,:];matrices[i,:3,3]=p
  world=[]
  for m,bone in zip(matrices,self.rig['bones']):world.append(m if bone['parent']<0 else world[bone['parent']]@m)
  return np.asarray(world)

def skin(rig,world,floor=0):
 delta=world@np.array([b['inverse'] for b in rig['bones']]);normals=np.linalg.inv(delta[:,:3,:3]).transpose(0,2,1);result=[]
 for part in rig['parts']:
  v=part['v'];out=np.zeros(len(v),dtype=STRIDE);out['uv']=v['uv']
  if part['skinned']:
   weights=v['w'].astype(float)/v['w'].sum(axis=1)[:,None];p=np.c_[v['p'],np.ones(len(v))];posed=np.zeros((len(v),3));normal=np.zeros_like(posed)
   for k in range(8):
    joints=np.where(weights[:,k]>0,v['j'][:,k],0);posed+=(delta[joints,:3,:]@p[:,:,None])[:,:,0]*weights[:,k,None];normal+=(normals[joints]@v['n'][:,:,None])[:,:,0]*weights[:,k,None]
  else:posed=v['p'].copy();normal=v['n'].copy()
  normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12);out['p']=posed;out['p'][:,1]-=floor;out['n']=normal
  if not np.isfinite(out.view('<f4')).all() or np.abs(out['p']).max()>10000:raise ValueError('Pose fora dos limites nativos.')
  result.append(out)
 return result

def write_model(rig,vertices,path):
 with Path(path).open('wb') as f:
  f.write(b'FF3D0001'+struct.pack('<II',len(rig['parts']),len(rig['textures'])))
  for part,v in zip(rig['parts'],vertices):
   f.write(struct.pack('<IIii7f',len(v),len(part['idx']),part['texture'],part['blend'],part['alpha'],*part['color'],*part['tint']));f.write(v.tobytes());f.write(part['idx'].tobytes())
  for w,h,kind,data in rig['textures']:f.write(struct.pack('<4I',w,h,kind,len(data))+data)
  f.write(b'FFMAT001'+struct.pack('<I',len(rig['parts'])))
  for p in rig['parts']:f.write(struct.pack('<Ii',int('/hair/' in p['asset'].lower()),p['coeff']))

def encode(v,indices):
 p=v['p'];n=v['n'].copy();n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8);uv=v['uv'];ids=indices.reshape(-1,3).copy();sign=np.einsum('ij,ij->i',np.cross(p[ids[:,1]]-p[ids[:,0]],p[ids[:,2]]-p[ids[:,0]]),n[ids].mean(axis=1));rev=sign<-.00001;ids[rev]=ids[rev][:,[0,2,1]]
 a,b,c=ids.T;e1=p[b]-p[a];e2=p[c]-p[a];d1=uv[b]-uv[a];d2=uv[c]-uv[a];det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0];tg=(e1*d2[:,1,None]-e2*d1[:,1,None])/np.where(abs(det)>1e-10,det,1)[:,None];tg[abs(det)<=1e-10]=0;acc=np.zeros_like(p)
 for k in range(3):np.add.at(acc,ids[:,k],tg)
 acc-=n*np.sum(acc*n,axis=1,keepdims=True);bad=np.linalg.norm(acc,axis=1)<1e-8;axis=np.zeros_like(p);axis[:,0]=1;axis[abs(n[:,0])>.9]=[0,0,1];acc[bad]=np.cross(axis[bad],n[bad]);acc/=np.maximum(np.linalg.norm(acc,axis=1,keepdims=True),1e-8)
 out=np.zeros(len(p),dtype=[('p','<f2',4),('n','<u4'),('g','<u4'),('uv','<f2',2)]);out['p'][:,:3]=p;out['p'][:,3]=1;out['n']=packed(n);out['g']=packed(acc);out['uv']=uv;return out.tobytes()

def bake(model,clip_path,output,read_asset,material_cache=None,cancel=None,player=None):
 rig=read_rig(model);kit_report=None
 if player:
  from kit_personalization import personalize
  rig,kit_report=personalize(rig,player,read_asset)
 anim=Animation(rig,json.loads(Path(clip_path).read_text(encoding='utf-8-sig')));initial=skin(rig,anim.pose(0));floor=min(v['p'][:,1].min() for v in initial);
 for v in initial:v['p'][:,1]-=floor
 intermediate=Path(output).parent/'player-static.ff3d';write_model(rig,initial,intermediate);report=convert(intermediate,output,read_asset,material_cache,animated=True)
 parts,_=read_model(intermediate);keys={};groups=collections.defaultdict(list)
 for i,p in enumerate(parts):
  key=(p['tex'],p['coeff'],tuple(p['tint'] if p['tex']>=0 else p['color']),p['alpha'],p['blend'],p['hair']);tile=keys.setdefault(key,len(keys));groups[(tile,p['blend'] or p['hair'])].append(i)
 plans={False:[],True:[]}
 for key,indices in sorted(groups.items()):
  group=[];n=0
  for i in indices:
   if n+len(initial[i])>58000:plans[key[1]].append(group);group=[];n=0
   group.append(i);n+=len(initial[i])
  if group:plans[key[1]].append(group)
 tracks=[]
 for alpha,offset in [(False,0),(True,64)]:
  for k,plan in enumerate(plans[alpha]):
   idx=[];n=0
   for i in plan:idx.append(rig['parts'][i]['idx']+n);n+=len(initial[i])
   tracks.append((offset+k,plan,np.concatenate(idx),n,[]))
 count=min(180,max(2,math.ceil(anim.duration*4)+1));native=Rx3((Path(output)/'geometry.rx3').read_bytes()).get(VERTEX)
 for frame,time in enumerate(np.linspace(0,anim.duration,count)):
  if cancel and cancel():raise InterruptedError('Visualização substituída por uma nova seleção.')
  vertices=initial if frame==0 else skin(rig,anim.pose(float(time)),floor)
  for slot,plan,idx,n,frames in tracks:
   data=encode(np.concatenate([vertices[i] for i in plan]),idx)
   if frame==0 and data!=native[slot][16:16+len(data)]:raise ValueError('Layout de vértices diferente da geometria nativa.')
   frames.append(data)
 target=Path(output)/'animation.bin'
 with target.open('wb') as f:
  f.write(struct.pack('<8sIIIf',b'FFPVTX01',len(tracks),count,rig['id'],anim.duration))
  for slot,plan,idx,n,frames in tracks:f.write(struct.pack('<II',slot,n));f.writelines(frames)
 report.update(player=rig['id'],animation_frames=count,animation_seconds=anim.duration,animation_bytes=target.stat().st_size)
 if kit_report:report['kit_personalization']=kit_report
 (Path(output)/'assets.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report
