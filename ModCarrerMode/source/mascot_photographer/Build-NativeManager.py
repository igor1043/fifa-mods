"""Map authored Mixamo skin to FIFA's fixed native manager palette.

Source weights are required. Geometry is fitted once to the native rest pose;
the manager inverse bind stays byte-for-byte unchanged. No runtime hook needed.
"""
from pathlib import Path
import argparse,sys,json,importlib.util,hashlib
import bpy
from mathutils import Vector,Matrix,Quaternion
import math
from mathutils.kdtree import KDTree

p=argparse.ArgumentParser()
p.add_argument('--source',required=True);p.add_argument('--output',required=True)
p.add_argument('--tools',required=True);p.add_argument('--template',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
src=Path(a.source);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('Build-MascotFromFbx.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
vertices,indices,name,unit=b.load_source_mesh(src)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
if len(meshes)!=1 or len(arms)!=1:raise ValueError('Expected one authored mesh and one armature')
mesh,arm=meshes[0],arms[0]
if any(not any(g.weight>1e-6 for g in v.groups) for v in mesh.data.vertices):
    raise ValueError('Source contains vertices without authored skin weights')
template=Path(a.template).read_bytes();parts,raw=b.read_model(b.Rx3(template))
if len(parts)!=1 or len(raw)!=31:raise ValueError('Expected native manager with one mesh and 31 bones')
native=[Matrix(tuple(tuple(m[c*4+r] for c in range(4)) for r in range(4))) for m in raw]
referenceHeight=max(parts[0]['positions'][1::3])-min(parts[0]['positions'][1::3])
floor=min(v['position'].y for v in vertices)
scale=referenceHeight/(max(v['position'].y for v in vertices)-floor)
centerX=(min(v['position'].x for v in vertices)+max(v['position'].x for v in vertices))*.5
offset=Vector((centerX,floor,0))
def normalized(point):return (b.game_position(point)*unit-offset)*scale
def joint(name):return normalized(arm.matrix_world@arm.data.bones['mixamorig:'+name].head_local)
# Retain the authored surface coordinates for reproducible, UV-aware texture
# repairs. These are source coordinates, before native rest-pose fitting.
surface=dict(vertices=[dict(position=list(b.game_position(mesh.matrix_world@v.co)*unit*scale)) for v in mesh.data.vertices],
             faces=[list(f.vertices) for f in mesh.data.polygons],
             uvs=[list(loop.uv) for loop in mesh.data.uv_layers.active.data])
(out/'authored_surface.json').write_text(json.dumps(surface),encoding='utf8')
mapping={'Hips':2,'RightUpLeg':3,'RightLeg':4,'RightFoot':5,'RightToeBase':6,
 'LeftUpLeg':7,'LeftLeg':8,'LeftFoot':9,'LeftToeBase':10,
 'Spine':11,'Spine1':12,'Neck':13,'Head':14,
 'LeftShoulder':16,'LeftArm':17,'LeftForeArm':18,'LeftHand':19,
 'RightShoulder':21,'RightArm':22,'RightForeArm':23,'RightHand':24}
positions={j:joint(name) for name,j in mapping.items()}
positions[15]=normalized(arm.matrix_world@arm.data.bones['mixamorig:Head'].tail_local)
positions[20]=normalized(arm.matrix_world@arm.data.bones['mixamorig:LeftHand'].tail_local)
positions[25]=normalized(arm.matrix_world@arm.data.bones['mixamorig:RightHand'].tail_local)
ends={2:11,11:12,12:13,13:14,14:15,3:4,4:5,5:6,7:8,8:9,9:10,
      16:17,17:18,18:19,19:20,21:22,22:23,23:24,24:25}
fit={}
for j,end in ends.items():
    sourceAxis=positions[end]-positions[j];targetAxis=native[end].translation-native[j].translation
    rotation=sourceAxis.normalized().rotation_difference(targetAxis.normalized()).to_matrix().to_4x4()
    ratio=targetAxis.length/sourceAxis.length
    # Change limb length along its axis only. Uniform scaling enlarged the
    # forearm circumference while shrinking hands from an unrelated end bone.
    radial=1.0
    if j in (2,11,12,13,14):ratio=1
    if j in (19,24):ratio=.80;radial=.85
    axis=sourceAxis.normalized();stretch=Matrix.Identity(4)
    for row in range(3):
        for column in range(3):stretch[row][column]=(radial if row==column else 0)+(ratio-radial)*axis[row]*axis[column]
    fit[j]=Matrix.Translation(native[j].translation)@rotation@stretch@Matrix.Translation(-positions[j])
for j,parent in ((6,5),(10,9)):fit[j]=fit[parent].copy()
# Native SLC has one bone per hand, no independent finger channels. Bake a
# relaxed finger pose from the authored finger skin before collapsing it to
# the wrist, keeping palms unchanged and preserving a natural resting shape.
fingerFit={}
fingerAngles={'Index':(10,18,10),'Middle':(12,20,12),'Ring':(14,22,14),'Pinky':(16,24,16),'Thumb':(5,8,5)}
for side in ('Left','Right'):
    for finger,angles in fingerAngles.items():
        parent=Matrix.Identity(4)
        for segment,angle in enumerate(angles,1):
            name=side+'Hand'+finger+str(segment);bone=arm.data.bones['mixamorig:'+name]
            head=normalized(arm.matrix_world@bone.head_local);tail=normalized(arm.matrix_world@bone.tail_local)
            direction=(tail-head).normalized();axis=direction.cross(Vector((0,-1,0)))
            if axis.length<.001:raise ValueError('Finger curl axis is degenerate')
            rotation=Quaternion(axis.normalized(),math.radians(angle)).to_matrix().to_4x4()
            parent=parent@Matrix.Translation(head)@rotation@Matrix.Translation(-head)
            fingerFit[name]=parent.copy()
sourceNames={g.index:g.name.split(':')[-1] for g in mesh.vertex_groups}
tree=KDTree(len(mesh.data.vertices))
for v in mesh.data.vertices:tree.insert(normalized(mesh.matrix_world@v.co),v.index)
tree.balance()
spine2fraction=max(0,min(1,(joint('Spine2').y-positions[12].y)/(positions[13].y-positions[12].y)))
joints=[];weights=[];headCount=0;sideCorrections=0;sourceSkin=[]
for vertex in vertices:
    point=(vertex['position']-offset)*scale
    _,index,distance=tree.find(point)
    if distance>.001:raise ValueError('Source loop vertex did not match skin')
    influences={};headWeight=0;curled=Vector((0,0,0));curledNormal=Vector((0,0,0));curledTangent=Vector((0,0,0));sourceTotal=0
    for group in mesh.data.vertices[index].groups:
        if group.weight<=1e-6:continue
        name=sourceNames[group.group]
        curl=fingerFit.get(name,Matrix.Identity(4))
        curled+=(curl@point)*group.weight
        curledNormal+=(curl.to_3x3()@vertex['normal'])*group.weight
        curledTangent+=(curl.to_3x3()@vertex['tangent'])*group.weight
        sourceTotal+=group.weight
        if name=='Spine2':
            for j,fraction in ((12,1-spine2fraction),(13,spine2fraction)):
                influences[j]=influences.get(j,0)+group.weight*fraction
            continue
        j=mapping.get(name)
        if name.startswith('LeftHand'):j=19
        if name.startswith('RightHand'):j=24
        # Native managers use 19 active bones. Their toe endpoints exist in
        # the 31-entry bind but are not separate animation-palette channels.
        if j==6:j=5
        if j==10:j=9
        if j is None:raise ValueError('Unmapped source influence '+name)
        influences[j]=influences.get(j,0)+group.weight
        if name=='Head':headWeight+=group.weight
    # Face, beard and skull remain together; only the lower neck blends.
    if headWeight>=.55 or (point.y>=positions[14].y and headWeight>=.1):
        influences={14:1};headCount+=1
    if abs(point.x)>3:
        forbidden=({21,22,23,24} if point.x>0 else {16,17,18,19})
        if point.y<positions[2].y:forbidden|=({3,4,5,6} if point.x>0 else {7,8,9,10})
        sideCorrections+=sum(j in forbidden and w>1e-5 for j,w in influences.items())
        influences={j:w for j,w in influences.items() if j not in forbidden}
    chosen=sorted(influences.items(),key=lambda item:-item[1])[:4];total=sum(w for j,w in chosen)
    if total<=0:raise ValueError('Unweighted vertex after side filtering')
    q=[round(w/total*255) for j,w in chosen];q[0]+=255-sum(q);js=[j for j,w in chosen]
    point=curled/sourceTotal;vertex['normal']=curledNormal.normalized();vertex['tangent']=curledTangent.normalized()
    joints.extend(js+[0]*(4-len(js)));weights.extend(q+[0]*(4-len(q)))
    pos=Vector((0,0,0));normal=Vector((0,0,0));tangent=Vector((0,0,0))
    for j,w in zip(js,q):
        pos+=(fit[j]@point)*(w/255)
        normal+=(fit[j].to_3x3().inverted().transposed()@vertex['normal'])*(w/255)
        tangent+=(fit[j].to_3x3()@vertex['tangent'])*(w/255)
    sourceSkin.append(dict(sourceIndex=index,joints=js,weights=q))
    vertex['position']=pos;vertex['normal']=normal.normalized();vertex['tangent']=tangent.normalized()
    vertex['uv']=(vertex['uv'][0],1-vertex['uv'][1])
order=sorted({j for j,w in zip(joints,weights) if w})
nativePalette=b.Rx3(template).get(0x0f3861a2)[0]
nativeOrder=list(nativePalette[272:272+nativePalette[4]])
if set(order)!=set(nativeOrder):raise ValueError('Converted manager active bones differ from native manager palette')
result,checked,bind=b.build_rx3(template,vertices,indices,joints,weights,order)
rx=b.Rx3(result)
next(section for section in rx.sections if section[0]==0x0f3861a2)[1]=nativePalette
if rx.get(0xdf9aec1e)!=b.Rx3(template).get(0xdf9aec1e):raise ValueError('Native manager inverse bind changed')
rx.set_names([(kind,'manager_.FxRenderableSimple' if kind==0xd48d7880 else name) for kind,name in rx.names()])
dest=out/'package/data/sceneassets/slc';dest.mkdir(parents=True,exist_ok=True)
(dest/'specificmanager_1035_0_0.rx3').write_bytes(rx.build())
(out/'converted_mesh.json').write_text(json.dumps(dict(parts=checked,bind=bind)),encoding='utf8')
(out/'source_skin_map.json').write_text(json.dumps(sourceSkin),encoding='utf8')
report=dict(clubId=1035,source=str(src),sourceHadRig=True,sourceBones=len(arm.data.bones),sourceVertices=len(mesh.data.vertices),unweightedSourceVertices=0,exportVertices=len(vertices),triangles=len(indices)//3,bones=31,rigidHeadVertices=headCount,removedOppositeSideInfluences=sideCorrections,method='Authored Mixamo weights mapped to fixed native manager; source-to-native rest segment fitting; inverse bind unchanged',spine2NeckFraction=spine2fraction,sourceLandmarks={str(k):list(v) for k,v in positions.items()},templateSha256=hashlib.sha256(template).hexdigest(),sourceSha256=hashlib.sha256(src.read_bytes()).hexdigest(),usedBones=order,nativeInverseBindUnchanged=True)
report.update(limbFit='axial length only; no forearm volume scaling',handAxialScale=.80,handRadialScale=.85,fingerPose='authored finger weights baked into relaxed curl before native wrist mapping',fingerCurlDegrees=fingerAngles)
report.update(nativeActiveBoneCount=len(nativeOrder),nativeBonePaletteByteIdentical=True,toeEndpointsUseFootWeights=True,runtimeValidated=False)
(out/'conversion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'eduardo_authored_source.blend'))
print('NATIVE MANAGER CONVERTED',len(vertices),'vertices',len(indices)//3,'triangles',headCount,'rigid head',flush=True)
