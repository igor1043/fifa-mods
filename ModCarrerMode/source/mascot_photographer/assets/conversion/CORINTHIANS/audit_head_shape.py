"""Compare lower-head rigidity across twelve retargeted animation poses."""
from pathlib import Path
import argparse,json,sys
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--package',required=True)
p.add_argument('--baseline-model',required=True)
p.add_argument('--clips',required=True)
p.add_argument('--tools',required=True)
p.add_argument('--report',required=True)
a=p.parse_args()
tools=Path(a.tools)
sys.path[:0]=[str(tools),str(tools/'vendor/rx3tools'),str(Path(__file__).resolve().parents[3])]
from rx3 import Rx3,read_model
from audit_locomotion import matrices,skin,retarget
part,raw=read_model(Rx3((Path(a.package)/'model_animated.rx3').read_bytes()));part=part[0]
old,oldraw=read_model(Rx3(Path(a.baseline_model).read_bytes()));old=old[0]
assert raw==oldraw and part['positions']==old['positions']
bind=matrices(raw);xyz=np.asarray(part['positions']).reshape(-1,3)
js=np.asarray(part['joints']).reshape(-1,4);ws=np.asarray(part['weights']).reshape(-1,4)
rigid=np.sum(ws*(js==14),axis=1)==255
report=json.loads(Path(a.report).read_text(encoding='utf8'))
ids=np.array(report['changedIndices']);ids=ids[rigid[ids]]
anchors=np.flatnonzero(rigid&(xyz[:,1]>148)&(xyz[:,1]<160)&(abs(xyz[:,0])<5))
assert len(ids)>0 and len(anchors)>0
distance=np.linalg.norm(xyz[ids]-xyz[anchors].mean(axis=0),axis=1)
clips=Path(a.clips);ref=matrices(json.loads((clips/'walk_baked.json').read_text(encoding='utf8'))['referenceBind'])
results={}
for label in ('idle','walk','cheer'):
 clip=json.loads((clips/(label+'_baked.json')).read_text(encoding='utf8'))
 for fraction in (0.,.25,.5,.75):
  frame=clip['frames'][round((len(clip['frames'])-1)*fraction)]
  palette=retarget(frame,ref,bind)
  corrected=skin(part,palette,bind,np.arange(len(xyz)))
  baseline=skin(old,palette,bind,np.arange(len(xyz)))
  error=float(np.max(abs(np.linalg.norm(corrected[ids]-corrected[anchors].mean(axis=0),axis=1)-distance)))
  previous=float(np.max(abs(np.linalg.norm(baseline[ids]-baseline[anchors].mean(axis=0),axis=1)-distance)))
  assert error<.0001,(label,fraction,error)
  results[label+str(fraction)]={'originalMaxShapeErrorCm':previous,'correctedMaxShapeErrorCm':error}
print(json.dumps({'rigidChangedVertices':len(ids),'toleranceCm':.0001,'poses':results},indent=2))
