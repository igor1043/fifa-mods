"""Preserve authored Mixamo skin, map to the audited FIFA rig, protect mascot head."""
from pathlib import Path
import bpy,sys,json,importlib.util,struct
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree
import argparse
parser=argparse.ArgumentParser(description='Preserve authored Mixamo skin and export FIFA 16 mascot RX3')
parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
parser.add_argument('--tools',required=True);parser.add_argument('--clips',required=True)
parser.add_argument('--club-id',type=int,required=True);parser.add_argument('--club-name',required=True)
parser.add_argument('--repair-unweighted',action='store_true',help='Fill only unweighted source vertices from three weighted neighbours within 2 cm')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
ROOT=Path(args.output);ROOT.mkdir(parents=True,exist_ok=True)
TOOLS=Path(args.tools);SRC=Path(args.source);CLIPS=Path(args.clips)
spec=importlib.util.spec_from_file_location('builder',TOOLS/'Build-MascotFromFbx.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
vertices,indices,name,unit=b.load_source_mesh(next(SRC.glob('*.fbx')))
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
repaired=[]
unweighted=[v.index for v in mesh.data.vertices if not any(g.weight>1e-6 for g in v.groups)]
if unweighted and args.repair_unweighted:
    weighted=[v for v in mesh.data.vertices if any(g.weight>1e-6 for g in v.groups)]
    if len(weighted)<3:raise ValueError('Insufficient weighted source vertices')
    neighbour_tree=KDTree(len(weighted))
    for v in weighted:neighbour_tree.insert(b.game_position(mesh.matrix_world@v.co),v.index)
    neighbour_tree.balance()
    for index in unweighted:
        point=b.game_position(mesh.matrix_world@mesh.data.vertices[index].co)
        neighbours=neighbour_tree.find_n(point,3)
        if max(d for _,_,d in neighbours)>2:raise ValueError('Unweighted vertex lacks a local weighted neighbourhood')
        influence={};total=sum(1/max(d,1e-6) for _,_,d in neighbours)
        for _,other,d in neighbours:
            groups=[g for g in mesh.data.vertices[other].groups if g.weight>1e-6]
            norm=sum(g.weight for g in groups);fraction=(1/max(d,1e-6))/total
            for g in groups:influence[g.group]=influence.get(g.group,0)+fraction*g.weight/norm
        for group,weight in influence.items():mesh.vertex_groups[group].add([index],weight,'REPLACE')
        repaired.append(dict(index=index,neighbours=[dict(index=i,distanceCm=d) for _,i,d in neighbours]))
scale=180/(max(v['position'].y for v in vertices)-min(v['position'].y for v in vertices))
floor=min(v['position'].y for v in vertices)
center=Vector(((max(v['position'].x for v in vertices)+min(v['position'].x for v in vertices))/2,floor,(max(v['position'].z for v in vertices)+min(v['position'].z for v in vertices))/2))
def position(p):return (b.game_position(p)-center)*scale
kd=KDTree(len(mesh.data.vertices))
for v in mesh.data.vertices:kd.insert(b.game_position(mesh.matrix_world@v.co),v.index)
kd.balance()
mapping={'Hips':2,'RightUpLeg':3,'RightLeg':4,'RightFoot':5,'RightToeBase':6,'LeftUpLeg':7,'LeftLeg':8,'LeftFoot':9,'LeftToeBase':10,'Spine':11,'Spine1':12,'Spine2':13,'Neck':13,'Head':14,'LeftShoulder':16,'LeftArm':17,'LeftForeArm':18,'LeftHand':19,'RightShoulder':21,'RightArm':22,'RightForeArm':23,'RightHand':24}
names={g.index:g.name.split(':')[-1] for g in mesh.vertex_groups}
joints=[];weights=[];head_count=0;fixed_sides=0
hip_y=b.game_position(arm.matrix_world@arm.data.bones['mixamorig:Hips'].head_local).y
shoulder_y=min(b.game_position(arm.matrix_world@arm.data.bones['mixamorig:'+n].head_local).y for n in ['LeftArm','RightArm'])
shoulder_x=min(abs(b.game_position(arm.matrix_world@arm.data.bones['mixamorig:'+n].head_local).x) for n in ['LeftArm','RightArm'])
head_y=b.game_position(arm.matrix_world@arm.data.bones['mixamorig:Head'].head_local).y
neck_y=b.game_position(arm.matrix_world@arm.data.bones['mixamorig:Neck'].head_local).y
neck_span=head_y-neck_y
face_floor=head_y-neck_span*.33
neck_blend_floor=head_y-neck_span*.66
for v in vertices:
    _,idx,d=kd.find(v['position'])
    if d>.001:raise ValueError('Source loop vertex not matched')
    raw={};source_head=0
    for g in mesh.data.vertices[idx].groups:
        n=names[g.group];target=mapping.get(n)
        if n.startswith('LeftHand'):target=19
        if n.startswith('RightHand'):target=24
        if target is None and g.weight>1e-6:raise ValueError('Unmapped group '+n)
        if target is not None:raw[target]=raw.get(target,0)+g.weight
        if n=='Head':source_head+=g.weight
    y=v['position'].y;x=v['position'].x
    if source_head>=.55 or y>=head_y or (y>=face_floor and raw.get(13,0)+source_head>=.65):
        raw={14:1};head_count+=1
    # Only neck junction blends; the face/skull remain rigid together.
    elif source_head>0 and y>=neck_blend_floor:
        t=max(source_head,min(1,max(0,(y-neck_blend_floor)/(face_floor-neck_blend_floor))))
        raw={14:t,13:1-t}
    if y<hip_y and abs(x)>3:
        forbidden=set([3,4,5,6]) if x>0 else set([7,8,9,10])
        fixed_sides+=sum(k in forbidden and w>1e-5 for k,w in raw.items())
        raw={k:w for k,w in raw.items() if k not in forbidden}
    if abs(x)>shoulder_x and shoulder_y-18<y<neck_y and 14 not in raw:
        forbidden=set([21,22,23,24]) if x>0 else set([16,17,18,19])
        raw={k:w for k,w in raw.items() if k not in forbidden}
    chosen=sorted(raw.items(),key=lambda i:-i[1])[:4]
    if not chosen:raise ValueError('Unweighted vertex')
    total=sum(w for _,w in chosen);q=[round(w/total*255) for _,w in chosen];q[0]+=255-sum(q)
    joints.extend([k for k,_ in chosen]+[0]*(4-len(chosen)));weights.extend(q+[0]*(4-len(chosen)))
    v['position']=(v['position']-center)*scale
    v['uv']=(v['uv'][0],1-v['uv'][1])
template=(TOOLS/'assets/template_model_animated.rx3').read_bytes()
_,bones=b.read_model(b.Rx3(template));positions={i:Vector(bones[i][12:15]) for i in range(31)}
for n,i in mapping.items():
    if n=='Spine2':continue
    positions[i]=position(arm.matrix_world@arm.data.bones['mixamorig:'+n].head_local)
positions[15]=position(arm.matrix_world@arm.data.bones['mixamorig:Head'].tail_local)
positions[20]=position(arm.matrix_world@arm.data.bones['mixamorig:LeftHand'].tail_local)
positions[25]=position(arm.matrix_world@arm.data.bones['mixamorig:RightHand'].tail_local)
positions[26]=positions[9].copy();positions[27]=positions[5].copy()
for i in (0,1,28,29,30):positions[i]=Vector((0,0,0))
order=sorted({j for j,w in zip(joints,weights) if w})
# Convert the source T rest pose to FIFA's asymmetric A rest pose once.
# Animation deltas otherwise leave T-pose shoulders raised in standing idle.
canonical=json.loads((CLIPS/'walk_baked.json').read_text(encoding='utf8'))['referenceBind']
parents=[-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0]
correction=[Quaternion() for _ in range(31)]
for j,c in ((17,18),(18,19),(22,23),(23,24)):
    direction=Vector(canonical[c][12:15])-Vector(canonical[j][12:15])
    correction[j]=(positions[c]-positions[j]).normalized().rotation_difference(direction.normalized())
for j,p in ((19,18),(20,18),(24,23),(25,23)):correction[j]=correction[p].copy()
old=[];new=[];newPositions={}
for j,parent in enumerate(parents):
    matrix=Matrix(tuple(tuple(bones[j][c*4+r] for c in range(4)) for r in range(4)))
    matrix.translation=positions[j];old.append(matrix)
    newPositions[j]=positions[j] if parent<0 or j==2 else newPositions[parent]+correction[parent]@(positions[j]-positions[parent])
    new.append(Matrix.LocRotScale(newPositions[j],correction[j]@matrix.to_quaternion(),Vector((1,1,1))))
skinMatrices=[new[j]@old[j].inverted() for j in range(31)]
for i,v in enumerate(vertices):
    p=Vector((0,0,0));n=Vector((0,0,0));t=Vector((0,0,0))
    for j,w in zip(joints[i*4:i*4+4],weights[i*4:i*4+4]):
        if w:
            p+=(skinMatrices[j]@v['position'])*(w/255)
            n+=(skinMatrices[j].to_3x3()@v['normal'])*(w/255)
            t+=(skinMatrices[j].to_3x3()@v['tangent'])*(w/255)
    v['position']=p;v['normal']=n.normalized();v['tangent']=t.normalized()
transforms={}
for j in range(31):
    q=new[j].to_quaternion();transforms[j]=dict(position=list(new[j].translation),quaternion=[q.x,q.y,q.z,q.w])
result,parts,bind=b.build_rx3(template,vertices,indices,joints,weights,order,bind_transforms=transforms)
dest=ROOT/'package/data/sceneassets/mascot'/str(args.club_id);dest.mkdir(parents=True,exist_ok=True)
for n in ('model.rx3','model_animated.rx3'):(dest/n).write_bytes(result)
(ROOT/'converted_mesh.json').write_text(json.dumps(dict(parts=parts,bind=bind)),encoding='utf8')
(ROOT/'conversion.json').write_text(json.dumps(dict(clubId=args.club_id,clubName=args.club_name,source=str(next(SRC.glob('*.fbx'))),heightCm=180,scale=scale,sourceVertices=len(mesh.data.vertices),exportVertices=len(vertices),triangles=len(indices)//3,rigidHeadVertices=head_count,removedOppositeLegInfluences=fixed_sides,repairedUnweightedSourceVertices=repaired,boneMap=mapping,usedBones=order),indent=2),encoding='utf8')
print('CONVERTED',len(vertices),len(indices)//3,head_count,'rigid head vertices')
