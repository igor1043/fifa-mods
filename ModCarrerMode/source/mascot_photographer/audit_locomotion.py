"""Read-only audit of the exact runtime retarget and installed RX3 foot skin."""
import argparse, json, sys, struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

PARENTS=[-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0]

def matrices(raw):
    return np.array(raw).reshape(31,4,4).transpose(0,2,1)

def retarget(frame, reference, bind):
    src=matrices(frame['matrices'])
    delta=R.from_matrix(src[:,:3,:3])*R.from_matrix(reference[:,:3,:3]).inv()
    out=np.zeros((31,4,4));out[:,3,3]=1
    out[:,:3,:3]=(delta*R.from_matrix(bind[:,:3,:3])).as_matrix()
    for j,parent in enumerate(PARENTS):
        out[j,:3,3]=bind[j,:3,3] if parent<0 or j==2 else out[parent,:3,3]+delta[parent].apply(bind[j,:3,3]-bind[parent,:3,3])
    return out

def skin(part, poses, bind, ids):
    xyz=np.array(part['positions']).reshape(-1,3)
    js=np.array(part['joints']).reshape(-1,4)
    ws=np.array(part['weights']).reshape(-1,4)/255
    hom=np.c_[xyz[ids],np.ones(len(ids))]
    sk=poses@np.linalg.inv(bind)
    return sum(np.einsum('nij,nj->ni',sk[js[ids,k]],hom)[:,:3]*ws[ids,k,None] for k in range(4))

def audit(part,bind,reference,clip):
    xyz=np.array(part['positions']).reshape(-1,3)
    js=np.array(part['joints']).reshape(-1,4);ws=np.array(part['weights']).reshape(-1,4)/255
    ids=[]
    for chain in ([5,6,27],[9,10,26]):
        idx=np.where(((np.isin(js,chain)*ws).sum(axis=1)>.7)&(xyz[:,1]<xyz[:,1].min()+14))[0]
        if len(idx)<8:raise ValueError('Insufficient independent foot vertices')
        ids.append(idx)
    feet=[]
    poses=[]
    for frame in clip['frames']:
        pose=retarget(frame,reference,bind);poses.append(pose)
        feet.append([skin(part,pose,bind,idx).mean(axis=0) for idx in ids])
    feet=np.array(feet)
    # The stance foot moves backwards in local Z while its opposite swings
    # forwards. Height alone chose the swing foot in the previous estimator.
    backward=-np.diff(feet[:,:,2],axis=0)
    support=np.argmax(backward,axis=1)
    delta=backward[np.arange(len(backward)),support]
    distance=np.r_[0,np.cumsum(np.maximum(delta,0))]
    old=np.array(clip['distanceCm'])
    return dict(duration=clip['duration'],footVertices=list(map(len,ids)),
                oldStrideCm=float(old[-1]),strideCm=float(distance[-1]),
                oldZeroIntervals=int((np.diff(old)<1e-6).sum()),
                newZeroIntervals=int((np.diff(distance)<1e-6).sum()),
                footCentres=feet.tolist(),contactSide=support.tolist(),
                distanceCm=distance.tolist(),times=[f['time'] for f in clip['frames']],
                oldContactSlipCm=float(np.mean(np.abs(-delta+np.diff(old)))),
                newContactSlipCm=float(np.mean(np.abs(-delta+np.diff(distance)))))

def foot_markers(part,bind):
    xyz=np.array(part['positions']).reshape(-1,3)
    js=np.array(part['joints']).reshape(-1,4);ws=np.array(part['weights']).reshape(-1,4)/255
    markers=np.zeros((2,31,4));centres=[]
    inverse=np.linalg.inv(bind)
    for side,chain in enumerate(([5,6,27],[9,10,26])):
        ids=np.where(((np.isin(js,chain)*ws).sum(axis=1)>.7)&(xyz[:,1]<xyz[:,1].min()+14))[0]
        if len(ids)<8:raise ValueError('Insufficient independent foot vertices')
        hom=np.c_[xyz[ids],np.ones(len(ids))];centres.append(xyz[ids].mean(axis=0))
        for slot in range(4):
            for bone in np.unique(js[ids,slot]):
                chosen=js[ids,slot]==bone
                markers[side,bone]+=((hom[chosen]@inverse[bone].T)*ws[ids[chosen],slot,None]).sum(axis=0)/len(ids)
    return struct.pack('<4If',0x3146534d,1,31,248,min(c[1] for c in centres))+markers.astype('<f4').tobytes()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tools',required=True);parser.add_argument('--study',required=True)
    parser.add_argument('--game',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--marker-dir')
    args=parser.parse_args();sys.path.insert(0,str(Path(args.tools)/'vendor/rx3tools'))
    from rx3 import Rx3,read_model
    study=Path(args.study);clip=json.loads((study/'walk_baked.json').read_text())
    reference=matrices(clip['referenceBind']);results={}
    package_root=Path(args.game)/'data/sceneassets/mascot'
    for folder in sorted(package_root.iterdir()):
        if not folder.is_dir() or not folder.name.isdecimal():continue
        club=int(folder.name)
        path=Path(args.game)/f'data/sceneassets/mascot/{club}/model_animated.rx3'
        if not path.exists():continue
        parts,raw=read_model(Rx3(path.read_bytes()));bind=matrices(raw)
        results[str(club)]=audit(parts[0],bind,reference,clip)
        if args.marker_dir:
            dest=Path(args.marker_dir)/str(club);dest.mkdir(parents=True,exist_ok=True)
            (dest/'locomotion_feet.bin').write_bytes(foot_markers(parts[0],bind))
    Path(args.output).write_text(json.dumps(results,indent=2),encoding='utf-8')
    for club,r in results.items():
        print(club, {k:r[k] for k in ('oldStrideCm','strideCm','oldZeroIntervals','newZeroIntervals','oldContactSlipCm','newContactSlipCm')})

if __name__=='__main__':main()
