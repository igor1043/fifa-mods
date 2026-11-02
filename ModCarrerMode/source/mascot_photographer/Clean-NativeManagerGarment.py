"""Clean concealed body geometry without altering exposed skin, bind or weights.

Run with Blender Python. A triangle must be skin coloured at its vertices and
centre, and all four outward samples must intersect garment geometry.
"""
from pathlib import Path
import bpy,sys,json,numpy as np,struct,hashlib,shutil
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import argparse
parser=argparse.ArgumentParser(description='Remove skin faces fully occluded by a garment in the source rest pose')
parser.add_argument('--model',required=True);parser.add_argument('--tools',required=True);parser.add_argument('--texture-rgb',required=True);parser.add_argument('--report',required=True)
parser.add_argument('--source-model');parser.add_argument('--source-blend');parser.add_argument('--source-points');parser.add_argument('--source-map');parser.add_argument('--unit-scale',type=float,default=1)
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);path=Path(a.model)
sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
from rx3 import Rx3,read_model,INDEX
rx=Rx3(path.read_bytes());parts,_=read_model(rx);part=parts[0];uv=np.array(part['uvs']).reshape(-1,2)
if a.source_model:
    sourceParts,_=read_model(Rx3(Path(a.source_model).read_bytes()));source=sourceParts[0];orig=np.array(source['positions']).reshape(-1,3);sourceTri=np.array(source['indices']).reshape(-1,3);tri=sourceTri.copy()
else:
    if not all((a.source_blend,a.source_points,a.source_map)):raise ValueError('FBX cleanup requires source blend, points and vertex map')
    bpy.ops.wm.open_mainfile(filepath=a.source_blend)
    mesh=next(o.data for o in bpy.context.scene.objects if o.type=='MESH');mesh.calc_loop_triangles();sourceTri=np.array([tuple(t.vertices) for t in mesh.loop_triangles],dtype=int)
    mapping=json.loads(Path(a.source_map).read_text());inverse={}
    for i,j in enumerate(mapping):inverse[(j,round(float(uv[i,0]),5),round(float(uv[i,1]),5))]=i
    sourceUv=mesh.uv_layers.active
    tri=[]
    for face in mesh.loop_triangles:
        indices=[]
        for lid in face.loops:
            loop=mesh.loops[lid];coords=sourceUv.data[lid].uv
            key=(loop.vertex_index,round(float(np.float16(coords.x)),5),round(float(np.float16(coords.y)),5))
            indices.append(inverse[key])
        tri.append(indices)
    tri=np.array(tri);orig=np.load(a.source_points)['positions']*a.unit_scale
image=np.load(a.texture_rgb)/255;h,w=image.shape[:2]
def sample(coords):
    return image[np.clip((coords[:,1]*h).astype(int),0,h-1),np.clip((coords[:,0]*w).astype(int),0,w-1)]
def skin(rgb):return (rgb[:,0]>.25)&(rgb[:,0]>rgb[:,1]*1.1)&(rgb[:,1]>rgb[:,2]*1.02)
faceSkin=skin(sample(uv[tri].mean(1)))
for k in range(3):faceSkin&=skin(sample(uv[tri[:,k]]))
faceCloth=~skin(sample(uv[tri].mean(1)))
bvh=BVHTree.FromPolygons([Vector(p) for p in orig],[tuple(t) for t in sourceTri[faceCloth]],all_triangles=True)
removed=[];maxDistance=0
for i in np.where(faceSkin)[0]:
    pts=orig[sourceTri[i]];center=pts.mean(0)
    if not (115<center[1]<155 and 8<abs(center[0])<35):continue
    normal=Vector(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
    if normal.length<1e-9:continue
    normal.normalize();samples=[center,*[p*.8+center*.2 for p in pts]];distances=[]
    for p in samples:
        hit,n,face,distance=bvh.ray_cast(Vector(p)+normal*.005,normal,6)
        if hit is None or n.dot(normal)<.1:break
        distances.append(distance)
    if len(distances)==4:removed.append(int(i));maxDistance=max(maxDistance,max(distances))
mask=np.ones(len(tri),dtype=bool);mask[removed]=False;kept=tri[mask].reshape(-1);assert len(removed)<len(tri)*.3
size=(16+len(kept)*2+15)&~15;data=bytearray(size);struct.pack_into('<4I',data,0,size,len(kept),2,0);struct.pack_into('<'+str(len(kept))+'H',data,16,*kept.tolist());next(s for s in rx.sections if s[0]==INDEX)[1]=bytes(data)
section=next(s for s in rx.sections if s[0]==0x22B2BE36);data=bytearray(section[1]);struct.pack_into('<3I',data,16,size,len(kept),2);section[1]=bytes(data);path.write_bytes(rx.build())
report={'removedConcealedSkinTriangles':len(removed),'keptTriangles':len(kept)//3,'method':'Four outward rays per skin face must hit the garment with consistent normals in the source rest pose','maxCoverDistanceCm':maxDistance,'sourceTriangleIds':removed,'runtimeValidated':False}
Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf8');print('OCCLUDED SKIN REVIEW',len(removed),'of',len(tri),'faces',flush=True)
