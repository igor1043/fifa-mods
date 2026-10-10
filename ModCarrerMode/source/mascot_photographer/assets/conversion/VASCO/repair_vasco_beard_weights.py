"""Adjust only Vasco beard/head attachment weights, preserving RX3 geometry."""
from pathlib import Path
import argparse,sys,struct,json,hashlib,os
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
parser=argparse.ArgumentParser()
parser.add_argument('--package',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args();package=Path(args.package);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,os.environ.get('FIFA_RX3_TOOLS',r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster\vendor\rx3tools'))
from rx3 import Rx3,read_model,FORMAT,VERTEX
# Colour extraction follows the validated existing RX3 texture reader.
sys.path.insert(0,r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster')
from texture_assets import rx3_colour_png
import io
raw=(package/'model_animated.rx3').read_bytes();rx=Rx3(raw);parts,bind=read_model(rx);part=parts[0]
xyz=np.array(part['positions']).reshape(-1,3);uv=np.array(part['uvs']).reshape(-1,2)
joints=np.array(part['joints']).reshape(-1,4);weights=np.array(part['weights']).reshape(-1,4)
image=Image.open(io.BytesIO(rx3_colour_png(package/'textures.rx3'))).convert('RGB');pixels=np.asarray(image)
col=pixels[np.clip((uv[:,1]*(image.height-1)).astype(int),0,image.height-1),np.clip((uv[:,0]*(image.width-1)).astype(int),0,image.width-1)]/255
neck,head=np.array(bind[13][12:15]),np.array(bind[14][12:15]);span=head[1]-neck[1]
brown=(col[:,0]>col[:,1]*1.2)&(col[:,1]>col[:,2]*1.08)&(col[:,0]>.12)&(col[:,0]<.8)
region=(xyz[:,1]>neck[1]-.5*span)&(xyz[:,1]<head[1]+.35*span)&(np.abs(xyz[:,0]-head[0])<1.5*span)&(xyz[:,2]>head[2]+1)
# Keep the connected beard surface, excluding brown/red shading on the shirt badge.
seeds=np.flatnonzero(brown&region)
pairs=cKDTree(xyz[seeds]).query_pairs(2.2,output_type='ndarray')
graph=coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(seeds),len(seeds)))
_,labels=connected_components(graph,directed=False)
largest=seeds[labels==np.bincount(labels).argmax()]
near,_=cKDTree(xyz[largest]).query(xyz)
beard_floor=float(xyz[largest,1].min())
weak_hair=(col[:,0]>col[:,1]*1.08)&(col[:,1]>col[:,2]*.95)&(col[:,0]>.015)
core=weak_hair&region&(near<3.5)&(xyz[:,1]>beard_floor-1)
if core.sum()<100:raise ValueError('Beard selection is unexpectedly small')
distances,_=cKDTree(xyz[core]).query(xyz)
oldhead=np.sum(weights*(joints==14),axis=1)/255
oldneck=np.sum(weights*(joints==13),axis=1)/255
transition=region&~core&(distances<3)&(oldhead>.3)&(oldhead+oldneck>.75)&(xyz[:,1]>neck[1])
changed=[];js=joints.copy();ws=weights.copy()
for i in np.flatnonzero(core|transition):
 h=1.0 if core[i] else max(oldhead[i],.85*(1-distances[i]/3))
 if h<=oldhead[i]+1e-5:continue
 wh=round(h*255);js[i]=[14,13,0,0];ws[i]=[wh,255-wh,0,0]
 if not np.array_equal(js[i],joints[i]) or not np.array_equal(ws[i],weights[i]):changed.append(int(i))
fields={}
for token in rx.get(FORMAT)[0][16:].split(b'\0')[0].decode().split():
 semantic,off,_,_,fmt=token.split(':');fields[semantic]=(int(off,16),fmt)
assert fields['i0'][1]=='4u8' and fields['w0'][1]=='4u8n'
entries=[struct.unpack_from('<4I',raw,16+16*i) for i in range(struct.unpack_from('<I',raw,12)[0])]
vb=next(e for e in entries if e[0]==VERTEX);stride=struct.unpack_from('<I',raw,vb[1]+8)[0];result=bytearray(raw);allowed=set()
for i in changed:
 at=vb[1]+16+i*stride
 for semantic,values in [('i0',js[i]),('w0',ws[i])]:
  start=at+fields[semantic][0];result[start:start+4]=bytes(values.tolist());allowed.update(range(start,start+4))
# No remap change is needed: the same 31-bone palette remains in use.
assert {int(j) for j,w in zip(js.flat,ws.flat) if w}=={int(j) for j,w in zip(joints.flat,weights.flat) if w}
assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(raw,result)))
checked,bones=read_model(Rx3(result));checked=checked[0]
for key in ['positions','normals','tangents','uvs','indices']:
 if key in part:assert checked[key]==part[key],key
assert bind==bones and np.all(ws.sum(axis=1)==255)
assert np.all(np.sum(ws*(js==14),axis=1)[core]==255)
for name in ['model.rx3','model_animated.rx3']:(out/name).write_bytes(result)
report={'club':569,'beardVertices':int(core.sum()),'changedVertices':len(changed),'changedBeardVertices':int(sum(core[i] for i in changed)),'changedTransitionVertices':int(sum(transition[i] for i in changed)),'changedIndices':changed,'geometryUvBindPreserved':True,'method':'front brown beard region anchored to head; 3 cm neck attachment blend; RX3 skin bytes only','sha256':hashlib.sha256(result).hexdigest()}
(out/'beard_weights_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='changedIndices'}))
