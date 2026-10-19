"""Refine a converted manager's forearm surface and continuous wrist skin.

Run inside Blender. Uses authored source coordinates to scope edits; leaves
the native inverse bind, topology, UVs, face and fingers unchanged.
"""
from pathlib import Path
import argparse,sys,json,importlib.util,math,struct
import bpy,numpy as np
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--surface',required=True);p.add_argument('--skin-map',required=True);p.add_argument('--conversion',required=True);p.add_argument('--tools',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
from rx3 import Rx3,read_model,VERTEX,FORMAT
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('Build-MascotFromFbx.py'));builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
source=Path(a.input);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
original=source.read_bytes();parts,bind=read_model(Rx3(original));part=parts[0]
rows=json.loads(Path(a.skin_map).read_text(encoding='utf8'));surface=json.loads(Path(a.surface).read_text(encoding='utf8'));conversion=json.loads(Path(a.conversion).read_text(encoding='utf8'))
src=np.array([surface['vertices'][row['sourceIndex']]['position'] for row in rows]);xyz=np.array(part['positions']).reshape(-1,3);old=xyz.copy();x=np.abs(src[:,0]);y=src[:,1]
js=np.array(part['joints']).reshape(-1,4);ws=np.array(part['weights']).reshape(-1,4);oldJs=js.copy();oldWs=ws.copy()
def smooth(lo,hi,value):
    t=np.clip((value-lo)/(hi-lo),0,1);return t*t*(3-2*t)
envelope=smooth(47,51,x)*(1-smooth(66,70,x))*(y>130)
# UV seams duplicate positions. Weld only the relaxation graph; retain every
# exported vertex and chart. Neighbour averages use edge length weights so
# dense UV seams cannot pull the forearm to one side.
keys=np.round(xyz,4);_,weld,inverse=np.unique(keys,axis=0,return_index=True,return_inverse=True)
points=xyz[weld].copy();alpha=np.zeros(len(points));np.maximum.at(alpha,inverse,envelope)
tri=np.array(part['indices']).reshape(-1,3);wtri=inverse[tri]
edges=np.unique(np.sort(np.r_[wtri[:,[0,1]],wtri[:,[1,2]],wtri[:,[2,0]]],axis=1),axis=0);edges=edges[edges[:,0]!=edges[:,1]]
rowsGraph=np.r_[edges[:,0],edges[:,1]];colsGraph=np.r_[edges[:,1],edges[:,0]]
weights=1/np.maximum(np.linalg.norm(points[rowsGraph]-points[colsGraph],axis=1),.2);den=np.bincount(rowsGraph,weights=weights,minlength=len(points))
# Taubin's paired passes remove the cuff ridge without the progressive volume
# shrink of an ordinary Laplacian blur. The blend vanishes before the fingers.
for iteration in range(10):
    for amount in (.45,-.47):
        averages=np.zeros_like(points)
        for axis in range(3):averages[:,axis]=np.bincount(rowsGraph,weights=weights*points[colsGraph,axis],minlength=len(points))/np.maximum(den,1e-10)
        delta=(averages-points)*alpha[:,None]*amount;delta[den==0]=0;points+=delta
delta=points[inverse]-xyz;distance=np.linalg.norm(delta,axis=1);delta*=np.minimum(1,.9/np.maximum(distance,1e-9))[:,None];xyz+=delta
# The original automatic wrist blend varies around a ring: shirt-side points
# can still be forearm-driven while adjacent skin-side points are hand-driven.
# Use one longitudinal transition for the whole wrist, with continuous fade
# into the original skin on both ends. Do not change elbow/upper-arm weights.
reweighted=0
landmarks={int(j):np.array(v) for j,v in conversion['sourceLandmarks'].items()}
for i,row in enumerate(rows):
    point=src[i];side=1 if point[0]>0 else -1;forearm,hand=(18,19) if side>0 else (23,24)
    mask=math.prod((float(smooth(58,61,x[i])),float(1-smooth(69,72,x[i])),float(y[i]>130)))
    if mask<=0:continue
    # Source is horizontal and mirrored, so X gives a stable, ring-uniform
    # distance at the wrist independent of front/back surface bulges.
    wristX=(abs(landmarks[19][0])+abs(landmarks[24][0]))*.5
    handWeight=float(smooth(wristX-7,wristX+7,x[i]))
    influences={int(j):int(w)/255 for j,w in zip(js[i],ws[i]) if w}
    chain=influences.get(forearm,0)+influences.get(hand,0)
    if chain<.95:continue
    influences[hand]=influences.get(hand,0)*(1-mask)+chain*handWeight*mask
    influences[forearm]=influences.get(forearm,0)*(1-mask)+chain*(1-handWeight)*mask
    chosen=sorted(((j,w) for j,w in influences.items() if w>1e-6),key=lambda r:-r[1])[:4];total=sum(w for j,w in chosen)
    q=[round(w/total*255) for j,w in chosen];q[0]+=255-sum(q)
    js[i]=[j for j,w in chosen]+[0]*(4-len(chosen));ws[i]=q+[0]*(4-len(chosen));reweighted+=1
# Recalculate surface frames for the relaxed vertices only. Keep source face
# normals and all untouched tangent frames byte-equivalent after repacking.
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('Manager forearm refinement');mesh.from_pydata(xyz.tolist(),[],tri.tolist());mesh.update()
obj=bpy.data.objects.new('Eduardo native 31-bone surface',mesh);bpy.context.scene.collection.objects.link(obj)
uv=mesh.uv_layers.new()
for loop in mesh.loops:
    i=loop.vertex_index;uv.data[loop.index].uv=part['uvs'][i*2:i*2+2]
for poly in mesh.polygons:poly.use_smooth=True
mesh.calc_tangents(uvmap=uv.name)
normals=np.zeros_like(xyz);tangents=np.zeros_like(xyz)
for loop in mesh.loops:normals[loop.vertex_index]+=np.array(loop.normal);tangents[loop.vertex_index]+=np.array(loop.tangent)
vertices=[]
for i,point in enumerate(xyz):
    changed=envelope[i]>.001
    normal=Vector(normals[i] if changed else part['normals'][i*3:i*3+3]).normalized()
    tangent=Vector(tangents[i]).normalized()
    vertices.append(dict(position=Vector(point),normal=normal,tangent=tangent,uv=tuple(part['uvs'][i*2:i*2+2])))
order=sorted(set(js[ws>0].tolist()));result,checked,checkedBind=builder.build_rx3(original,vertices,part['indices'],js.ravel().tolist(),ws.ravel().tolist(),order)
assert Rx3(result).get(0xdf9aec1e)==Rx3(original).get(0xdf9aec1e)
assert checked[0]['indices']==part['indices'] and checked[0]['uvs']==part['uvs']
assert np.all(ws.sum(1)==255)
unchanged=(envelope==0)&(x<58)
assert np.array_equal(xyz[unchanged],old[unchanged])
# Restore exact packed frames outside the geometry repair, since read_model
# exposes normals but not the original packed tangent stream.
rx=Rx3(result);originalRx=Rx3(original);vb=bytearray(rx.get(VERTEX)[0]);oldVb=originalRx.get(VERTEX)[0];stride=struct.unpack_from('<I',vb,8)[0]
fields={}
for token in rx.get(FORMAT)[0][16:].split(b'\0')[0].decode().split():
    semantic,offset,*_=token.split(':');fields[semantic]=int(offset,16)
for i in np.where(envelope<=.001)[0]:
    for semantic in ('n0','g0'):
        at=16+int(i)*stride+fields[semantic];vb[at:at+4]=oldVb[at:at+4]
next(s for s in rx.sections if s[0]==VERTEX)[1]=bytes(vb);result=rx.build()
# Restoring the input native palette keeps its audited engine ordering.
next(s for s in rx.sections if s[0]==0x0f3861a2)[1]=originalRx.get(0x0f3861a2)[0];result=rx.build()
(out/source.name).write_bytes(result)
for i,row in enumerate(rows):
    row['joints']=[int(j) for j,w in zip(js[i],ws[i]) if w]
    row['weights']=[int(w) for w in ws[i] if w]
(out/'source_skin_map.json').write_text(json.dumps(rows),encoding='utf8')
report=dict(passed=True,smoothedVertices=int((envelope>.001).sum()),reweightedWristVertices=reweighted,maxSurfaceMovementCm=float(np.linalg.norm(xyz-old,axis=1).max()),nativeInverseBindUnchanged=True,topologyAndUVsUnchanged=True,sourceFbxUntouched=True,method='Bounded Taubin forearm surface relaxation and longitudinally consistent wrist weights')
(out/'forearm_geometry_review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'eduardo_refined_native_surface.blend'))
print(json.dumps(report,indent=2))
