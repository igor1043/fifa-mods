import bpy,sys,json,math,struct,numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
root=Path(r'J:\mods\fifa 16\estudos fifa 16\18_MASCOTE_POSICAO_MOVIMENTO_20261010')
tools=Path(r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster')
sys.path.insert(0,str(tools/'vendor/rx3tools'))
from rx3 import Rx3,read_model,invert4
parts,bindraw=read_model(Rx3((tools/'assets/specificballboy_0_1_0.rx3').read_bytes()))
def mat(a):return Matrix(tuple(tuple(a[c*4+r] for c in range(4)) for r in range(4)))
bind=[mat(a) for a in bindraw];bindq=[m.to_quaternion().normalized() for m in bind];bindp=[m.translation.copy() for m in bind]
parents=[-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0]
# Native branch sides are established from actual bind positions, not ID order.
mapping={2:'Hips',3:'RightUpLeg',4:'RightLeg',5:'RightFoot',7:'LeftUpLeg',8:'LeftLeg',9:'LeftFoot',11:'Spine1',12:'Spine3',13:'Neck1',14:'Head',16:'LeftShoulder',17:'LeftArm',18:'LeftForeArm',19:'LeftHand',21:'RightShoulder',22:'RightArm',23:'RightForeArm',24:'RightHand'}
source=json.loads((root/'slow_walk_loop.channels.json').read_text())
hierarchy={b['name']:b['parent'] for b in json.loads((tools/'assets/animation_library/player_hierarchy.json').read_text())}
index={name:i for i,name in enumerate(source['channels'])}
def quat(a):return Quaternion((a[3],a[0],a[1],a[2])).normalized()
def source_world(name,frame,cache):
 if name in cache:return cache[name]
 q=quat(frame[index[name+'.q']]) if frame is not None and name!='AITrajectory' and name+'.q' in index else quat(source['defaults'].get(name+'.q',[0,0,0,1]))
 # The VBR translation offsets remain experimental. Retain reference lengths.
 p=Vector(source['defaults'].get(name+'.t',[0,0,0]))
 m=Matrix.LocRotScale(p,q,Vector((1,1,1)))
 parent=hierarchy.get(name)
 if parent:m=source_world(parent,frame,cache)@m
 cache[name]=m;return m
sr={}
def sp(name):return source_world(name,None,sr).translation
x=(sp('LeftShoulder')-sp('RightShoulder')).normalized();up=(sp('Head')-sp('Hips')).normalized()
z=x.cross(up).normalized();y=z.cross(x).normalized()
sourceBasis=Matrix((x,y,z)).transposed().to_quaternion()
tx=(bindp[16]-bindp[21]).normalized();ty=(bindp[14]-bindp[2]).normalized();tz=tx.cross(ty).normalized();ty=tz.cross(tx).normalized()
targetBasis=Matrix((tx,ty,tz)).transposed().to_quaternion()
basis=targetBasis@sourceBasis.inverted()
restq={j:source_world(name,None,sr).to_quaternion() for j,name in mapping.items()}
# Foot samples from the actual reference skin for floor and stride estimation.
p=parts[0];positions=np.array(p['positions']).reshape((-1,3));js=np.array(p['joints']).reshape((-1,4));ws=np.array(p['weights']).reshape((-1,4))/255
floor=float(positions[:,1].min());footIds=[np.where((positions[:,1]<floor+18)&(positions[:,0]<0))[0],np.where((positions[:,1]<floor+18)&(positions[:,0]>0))[0]]
inv=[np.array(invert4(a)).reshape((4,4),order='F') for a in bindraw]
def skinfoot(matrices,ids):
 xyz=positions[ids];hom=np.c_[xyz,np.ones(len(xyz))];out=np.zeros_like(xyz)
 for slot in range(4):
  for j in np.unique(js[ids,slot]):
   choose=np.where(js[ids,slot]==j)[0]
   if len(choose):
    out[choose]+=(hom[choose]@(np.array(matrices[j])@inv[j]).T)[:,:3]*ws[ids[choose],slot,None]
 return out
def transforms(qs,hip=None):
 pp=[]
 for j,parent in enumerate(parents):
  if parent<0:pp.append(bindp[j].copy())
  elif j==2:pp.append(bindp[j].copy() if hip is None else hip.copy())
  else:pp.append(pp[parent]+(qs[parent]@bindq[parent].inverted())@(bindp[j]-bindp[parent]))
 return [Matrix.LocRotScale(pp[j],qs[j],Vector((1,1,1))) for j in range(31)]
walk=[];N=len(source['frames']);duration=source['duration']
for fi,frame in enumerate(source['frames']):
 t=source['times'][fi];blend=max(0,min(1,(t-(duration-.25))/.25));blend=blend*blend*(3-2*blend)
 adjusted=[]
 for j,value in enumerate(frame):
  if j<source['quaternions']:
   q=quat(value).slerp(quat(source['frames'][0][j]),blend);adjusted.append([q.x,q.y,q.z,q.w])
  else:adjusted.append(value)
 sw={};qs=[q.copy() for q in bindq]
 for j,name in mapping.items():
  delta=source_world(name,adjusted,sw).to_quaternion()@restq[j].inverted()
  qs[j]=basis@delta@basis.inverted()@bindq[j]
 # Source arms start in a T pose; target skin starts in an A pose.
 # Match the animated anatomical directions, not T-pose rotation deltas alone.
 for j,child in [(16,17),(17,18),(18,19),(21,22),(22,23),(23,24)]:
  direction=(basis@(source_world(mapping[child],adjusted,sw).translation-source_world(mapping[j],adjusted,sw).translation)).normalized()
  current=(qs[j]@bindq[j].inverted())@(bindp[child]-bindp[j])
  qs[j]=current.normalized().rotation_difference(direction)@qs[j]
 for j in [19,24]:
  parent=parents[j]
  # Neutral mitten wrist: inherit forearm instead of incompatible player hand twist.
  qs[j]=(qs[parent]@bindq[parent].inverted())@bindq[j]
 for j in range(31):
  if j not in mapping and parents[j]>=0:qs[j]=(qs[parents[j]]@bindq[parents[j]].inverted())@bindq[j]
 matrices=transforms(qs)
 heights=[float(skinfoot(matrices,ids)[:,1].min()) for ids in footIds]
 correction=floor-min(heights)
 for m in matrices:m.translation.y+=correction
 walk.append(matrices)
# Solve forward progress from the planted foot rather than the uncertain root track.
feet=[]
for matrices in walk:
 samples=[skinfoot(matrices,ids) for ids in footIds]
 feet.append([(float(a[:,1].min()),float(a[a[:,1]<=a[:,1].min()+2,2].mean())) for a in samples])
distance=[0.]
for i in range(1,N):
 support=0 if feet[i-1][0][0]<=feet[i-1][1][0] else 1
 delta=feet[i-1][support][1]-feet[i][support][1]
 distance.append(distance[-1]+max(0.,min(8.,delta)))
stride=distance[-1]
if stride<15 or stride>200:raise ValueError('Unusable stride '+str(stride))
clips=json.loads((tools/'assets/standing_clips.json').read_text())['clips']
def native_clip(ident):
 c=next(c for c in clips if c['id']==ident);result=[]
 first=[mat(c['frames'][0]['matrices'][j*16:(j+1)*16]) for j in range(31)]
 for f in c['frames']:
  alpha=max(0,min(1,(f['time']-(c['duration']-.25))/.25));alpha=alpha*alpha*(3-2*alpha)
  result.append([Matrix.LocRotScale(m.translation.lerp(first[j].translation,alpha),m.to_quaternion().slerp(first[j].to_quaternion(),alpha),Vector((1,1,1))) for j in range(31) for m in [mat(f['matrices'][j*16:(j+1)*16])]])
 return c,result
idle,ip=native_clip('idle_variant');cheer,cp=native_clip('celebrate')
def flat(m):return [m[r][c] for c in range(4) for r in range(4)]
def frames_json(poses,times):return [{'time':t,'matrices':[round(v,7) for m in mm for v in flat(m)]} for t,mm in zip(times,poses)]
export={'referenceBind':bindraw,'source':source['name'],'mapping':mapping,'duration':duration,'strideCm':stride,'frames':frames_json(walk,source['times']),'distanceCm':distance}
(root/'walk_baked.json').write_text(json.dumps(export),encoding='utf-8')
(root/'idle_baked.json').write_text(json.dumps({'duration':idle['duration'],'frames':frames_json(ip,[f['time'] for f in idle['frames']])}))
(root/'cheer_baked.json').write_text(json.dumps({'duration':cheer['duration'],'frames':frames_json(cp,[f['time'] for f in cheer['frames']])}))
def f(v):
 if abs(v)<1e-9:v=0.
 s=f'{v:.8g}'
 if '.' not in s and 'e' not in s:s+='.0'
 return s+'f'
def encode(name,poses):
 rows=[]
 for mats in poses:
  vals=[]
  for m in mats:
   q=m.to_quaternion().normalized();v=m.translation;vals.extend([v.x,v.y,v.z,q.x,q.y,q.z,q.w])
  rows.append(' {'+','.join(f(v) for v in vals)+'}')
 return f'static const float {name}[{len(poses)}][31*7]={{\n'+',\n'.join(rows)+'\n};\n'
header='#pragma once\n// Offline baked FIFA walk / standing idle / home-goal poses. No per-frame I/O.\n'
header+='static constexpr float mascotWalkDuration='+f(duration)+';\n'
header+='static constexpr float mascotWalkStride='+f(stride)+';\n'
header+='static constexpr unsigned int mascotWalkFrameCount='+str(len(walk))+';\n'
header+='static constexpr float mascotWalkTimes[]={'+','.join(f(t) for t in source['times'])+'};\n'
header+='static const float mascotWalkDistances[]={'+','.join(f(t) for t in distance)+'};\n'
header+='static constexpr unsigned int mascotIdleFrameCount='+str(len(ip))+';\n'
header+='static constexpr float mascotIdleDuration='+f(idle['duration'])+';\n'
header+='static const float mascotIdleTimes[]={'+','.join(f(a['time']) for a in idle['frames'])+'};\n'
header+='static constexpr unsigned int mascotCheerFrameCount='+str(len(cp))+';\n'
header+='static constexpr float mascotCheerDuration='+f(cheer['duration'])+';\n'
header+='static const float mascotCheerTimes[]={'+','.join(f(a['time']) for a in cheer['frames'])+'};\n'
header+='static const float mascotWalkBindPose[31*7]={'+','.join(f(v) for j in range(31) for v in [bindp[j].x,bindp[j].y,bindp[j].z,bindq[j].x,bindq[j].y,bindq[j].z,bindq[j].w])+'};\n'
header+=encode('mascotWalkFrames',walk)
header+=encode('mascotIdleFrames',ip)
header+=encode('mascotCheerFrames',cp)
dst=Path(r'U:\mods\FIFA Friends V12\ModCarrerMode\source\mascot_photographer\mascot_walk_clips.h')
dst.write_text(header,encoding='utf-8')
print(json.dumps({'frames':N,'duration':duration,'strideCm':stride,'speedCmPerSec':stride/duration,'header':str(dst),'mapLegRight':3,'mapLegLeft':7,'rootVectorUsed':False},ensure_ascii=False))
