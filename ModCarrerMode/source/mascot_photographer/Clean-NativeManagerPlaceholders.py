"""Remove the supplied head's untextured grey placeholder faces offline.

Require the known flat neutral texels at every sampled UV corner/centre and
the reserved upper hair chart. Keep real hair, scalp, face, UVs and vertices.
An optional BVH occlusion audit can remove independently verified buried skin.
"""
from pathlib import Path
import argparse,json,struct,sys
import numpy as np
from PIL import Image

def run(jobs,stage,textures,tools,occlusion=None):
 sys.path.insert(0,str(tools));from rx3 import Rx3,read_model,INDEX
 reports=[]
 for job in json.loads(Path(jobs).read_text(encoding='utf8')):
  sid=job['assetId'];folder=Path(stage)/f'data/sceneassets/manager_market/{sid}';rx=Rx3((folder/'model_0.rx3').read_bytes());parts,bind=read_model(rx);part=parts[0];p=np.array(part['positions']).reshape(-1,3);uv=np.array(part['uvs']).reshape(-1,2);tri=np.array(part['indices']).reshape(-1,3);image=np.asarray(Image.open(Path(textures)/f'{sid}-cm.png').convert('RGB'));h,w=image.shape[:2]
  def sample(coords):return image[np.clip((coords[:,1]*h).astype(int),0,h-1),np.clip((coords[:,0]*w).astype(int),0,w-1)].astype(int)
  mask=(p[tri][:,:,1]>140).all(1)&(uv[tri][:,:,0]>.666).all(1)&(uv[tri][:,:,1]>.828).all(1)
  for coords in [uv[tri].mean(1),*[uv[tri[:,i]] for i in range(3)]]:mask&=(np.abs(sample(coords)-[132,130,132])<=1).all(1)
  placeholder=np.where(mask)[0];buried=[]
  if occlusion and sid in occlusion:
   buried=json.loads(Path(occlusion[sid]).read_text(encoding='utf8'))['sourceTriangleIds']
   if any(i<0 or i>=len(tri) for i in buried):raise ValueError('Occlusion indices differ from source topology')
   mask[buried]=True
  if mask.sum()>=len(tri)*.15:raise ValueError('Excess placeholder removal')
  kept=tri[~mask].reshape(-1);size=(16+len(kept)*2+15)&~15;data=bytearray(size);struct.pack_into('<4I',data,0,size,len(kept),2,0);data[16:16+len(kept)*2]=kept.astype('<u2').tobytes();next(s for s in rx.sections if s[0]==INDEX)[1]=bytes(data);section=next(s for s in rx.sections if s[0]==0x22b2be36);data=bytearray(section[1]);struct.pack_into('<3I',data,16,size,len(kept),2);section[1]=bytes(data)
  result=rx.build() if mask.any() else (folder/'model_0.rx3').read_bytes();checked,cb=read_model(Rx3(result));assert cb==bind
  for field in ('positions','normals','uvs','joints','weights'):assert checked[0][field]==part[field]
  for weather in (0,1):(folder/f'model_{weather}.rx3').write_bytes(result)
  report=dict(assetId=sid,placeholderFacesRemoved=int(len(placeholder)),bvhVerifiedBuriedSkinFacesRemoved=len(buried),verticesUVsNormalsSkinBindPreserved=True);reports.append(report);print(json.dumps(report),flush=True)
 return reports

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--textures',type=Path,required=True);p.add_argument('--tools',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--occlusion-coach',type=int);p.add_argument('--occlusion',type=Path);a=p.parse_args();reports=run(a.manifest,a.stage,a.textures,a.tools,{a.occlusion_coach:a.occlusion} if a.occlusion else None);a.report.write_text(json.dumps(reports,indent=2),encoding='utf8')
