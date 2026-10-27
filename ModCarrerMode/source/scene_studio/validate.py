from pathlib import Path
import sys,json,hashlib
import numpy as np
from rig_io import read_rig,skin
root=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(__file__).resolve().parent/'export_engine'))
from native_assets import read_model
scene=json.loads((root/'assets/scene.json').read_text(encoding='utf8'))
report={'variants':[],'players':11,'bones_per_player':400,'max_skin_error_cm':0}
for variant in scene['variants']:
 parts,_=read_model(root/'assets'/(variant['id']+'.ff3d'));offset=0;changes=[]
 for player in variant['players']:
  rig=read_rig(root/'assets'/f'player-{player["id"]}.ff3d');assert len(rig['bones'])==400
  p=skin(rig,player['poseWorld']);shift=np.array(player['position'])
  for result in p:
   expected=parts[offset]['v']['p'];error=float(np.abs(result+shift-expected).max());report['max_skin_error_cm']=max(report['max_skin_error_cm'],error);assert error<.002,(player['name'],offset,error);offset+=1
 assert offset==len(parts)
 report['variants'].append(dict(id=variant['id'],players=len(variant['players']),parts=offset))
before,after=scene['variants']
for a,b in zip(before['players'],after['players']):
 assert a['id']==b['id'] and a['position']==b['position'] and a['crouching']==b['crouching']
rig=read_rig(root/'assets'/f'player-{before["players"][0]["id"]}.ff3d')
for a,b in zip(before['players'],after['players']):
 for joint,name in enumerate(q['name'] for q in rig['bones']):
  chain=[];parent=joint
  while parent>=0:chain.append(rig['bones'][parent]['name']);parent=rig['bones'][parent]['parent']
  if not any(any(t in bone for t in ('Arm','Hand','Elbow','Shoulder','Radialis')) for bone in chain):
   assert np.max(np.abs(np.array(a['poseWorld'][joint])-b['poseWorld'][joint]))<.002,name
report['candidate_changes_only_arms']=True
(root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
