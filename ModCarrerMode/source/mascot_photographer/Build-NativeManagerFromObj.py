"""Bind a static human OBJ to a native FIFA manager without runtime hooks.

Requires an explicit source joint profile and optional UV chart relocations.
Transfers weights from a native manager fitted to the source rest pose, then
fits the new mesh to native rest. Does not pretend the OBJ has authored skin.
Run with Blender's Python; inspect rendered poses before installing.
"""
from pathlib import Path
import sys,argparse,json,importlib.util,hashlib
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree

p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--profile',required=True);p.add_argument('--reference',required=True);p.add_argument('--tools',required=True);p.add_argument('--output',required=True);p.add_argument('--club-id',required=True,type=int)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);profile=json.loads(Path(a.profile).read_text(encoding='utf8'))
sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('Build-MascotFromFbx.py'));b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
raw=Path(a.reference).read_bytes();parts,bind=b.read_model(b.Rx3(raw));ref=parts[0]
native=[Matrix([m[i:i+4] for i in range(0,16,4)]).transposed() for m in bind]
points=[];uvs=[];faces=[];faceuv=[]
for row in Path(a.source).read_text(encoding='utf8').splitlines():
    t=row.split()
    if not t:continue
    if t[0]=='v':points.append(Vector(tuple(float(z)*profile['sourceScaleCm'] for z in t[1:4])))
    elif t[0]=='vt':uvs.append(tuple(map(float,t[1:3])))
    elif t[0]=='f':
        pairs=[v.split('/') for v in t[1:]];faces.append([int(v[0])-1 for v in pairs]);faceuv.extend([uvs[int(v[1])-1] for v in pairs])
if not points or not faces:raise ValueError('OBJ has no mesh')
headSurface=[False]*len(points);at=0
for face in faces:
    for i in face:
        if points[i].y>150 and faceuv[at][1]<.334:headSurface[i]=True
        at+=1
neckRepair=profile.get('neckClearance');neckBlend={};neckDisplacements={}
if neckRepair:
    # Contract only the neck surface covered by the high collar. Fade to
    # zero before the jaw/ears; the exposed face and glasses stay unchanged.
    def smooth(a,b,x):
        t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
    for i,point in enumerate(points):
        if not headSurface[i]:continue
        front=smooth(neckRepair['rearZ'],neckRepair['frontZ'],point.z)
        edge=neckRepair['rearHeight']*(1-front)+neckRepair['frontHeight']*front
        blend=1-smooth(edge,edge+neckRepair['featherCm'],point.y)
        if blend<=.001:continue
        axis=Vector((neckRepair['axisX'],point.y,neckRepair['axisZ']))
        delta=(axis-point)*neckRepair['radialContraction']*blend
        if delta.length>neckRepair['maxContractionCm']:delta*=neckRepair['maxContractionCm']/delta.length
        point+=delta;neckBlend[i]=blend;neckDisplacements[i]=delta.length
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('Source OBJ with reviewed UV charts');mesh.from_pydata([tuple(v) for v in points],[],faces);mesh.update();uv=mesh.uv_layers.new()
for loop,value in zip(mesh.loops,faceuv):
    point=points[loop.vertex_index];u,v=value
    for rule in profile.get('uvRelocations',[]):
        if rule['u'][0]<=u<rule['u'][1] and rule['v'][0]<=v<rule['v'][1] and rule['height'][0]<=point.y<rule['height'][1]:
            u+=rule['offset'][0];v+=rule['offset'][1];break
    uv.data[loop.index].uv=(u,1-v)
for poly in mesh.polygons:poly.use_smooth=True
mesh.calc_loop_triangles();mesh.calc_tangents(uvmap=uv.name)
uv=mesh.uv_layers.active
source={j:native[j].translation.copy() for j in range(31)}
source.update({int(j):Vector(v) for j,v in profile['sourceJointsCm'].items()})
ends={2:11,11:12,12:13,13:14,14:15,3:4,4:5,5:6,7:8,8:9,9:10,
      16:17,17:18,18:19,19:20,21:22,22:23,23:24,24:25};fit={j:Matrix.Identity(4) for j in range(31)}
for j,end in ends.items():
    axis=source[end]-source[j];target=native[end].translation-native[j].translation
    rotation=axis.normalized().rotation_difference(target.normalized()).to_matrix().to_4x4();ratio=target.length/axis.length
    if j in (2,11,12,13,14,19,24):ratio=1
    stretch=Matrix.Identity(4);direction=axis.normalized()
    for r in range(3):
        for c in range(3):stretch[r][c]=(1 if r==c else 0)+(ratio-1)*direction[r]*direction[c]
    fit[j]=Matrix.Translation(native[j].translation)@rotation@stretch@Matrix.Translation(-source[j])
for j,parent in ((6,5),(10,9)):fit[j]=fit[parent].copy()
inverse={j:m.inverted() for j,m in fit.items()}
reference=[];tree=KDTree(len(ref['positions'])//3)
for i in range(len(ref['positions'])//3):
    v=Vector(ref['positions'][i*3:i*3+3]);q=Vector()
    for j,w in zip(ref['joints'][4*i:4*i+4],ref['weights'][4*i:4*i+4]):q+=(inverse[j]@v)*(w/255)
    tree.insert(q,i);reference.append(q)
tree.balance();skin=[];distances=[]
for sourceIndex,point in enumerate(points):
    neighbours=tree.find_n(point,8);accum={}
    for _,i,distance in neighbours:
        for j,w in zip(ref['joints'][4*i:4*i+4],ref['weights'][4*i:4*i+4]):
            if w:accum[j]=accum.get(j,0)+w/(distance+.4)**2
    if point.y>157:
        if headSurface[sourceIndex] and point.y>161:accum={14:1}
        else:
            allowed=(12,13,14) if headSurface[sourceIndex] else (12,13)
            accum={j:w for j,w in accum.items() if j in allowed} or {13:1}
            if not headSurface[sourceIndex]:
                # A high zipped collar needs gradual head-follow at its top,
                # otherwise it remains upright while the chin rotates down.
                t=max(0,min(1,(point.y-157)/9));headMass=.8*t*t*(3-2*t);total=sum(accum.values())
                accum={j:w/total*(1-headMass) for j,w in accum.items()};accum[14]=headMass
    if abs(point.x)>27 and point.y>88:
        allowed=(16,17,18,19) if point.x>0 else (21,22,23,24);accum={j:w for j,w in accum.items() if j in allowed}
    if abs(point.x)>14 and 115<point.y<157:
        # Continuous anatomical shoulder/axilla blend, rather than a hard
        # X cutoff that makes a visible flap at the sleeve-to-torso seam.
        chain=(16,17,18,19) if point.x>0 else (21,22,23,24)
        arm={j:w for j,w in accum.items() if j in chain};body={j:w for j,w in accum.items() if j in (2,11,12,13)}
        if not arm:arm={17 if point.x>0 else 22:1}
        if not body:body={12 if point.y>126 else 11:1}
        inner=14+max(0,146-point.y)*.48
        t=max(0,min(1,(abs(point.x)-inner)/12));mass=t*t*(3-2*t)
        armTotal=sum(arm.values());bodyTotal=sum(body.values())
        accum={j:w/armTotal*mass for j,w in arm.items()}
        accum.update({j:w/bodyTotal*(1-mass) for j,w in body.items()})
    if point.y<90 and abs(point.x)>5:
        opposite=(3,4,5) if point.x>0 else (7,8,9);accum={j:w for j,w in accum.items() if j not in opposite}
    if not accum:raise ValueError('Unweighted vertex after anatomical filtering')
    selected=sorted(accum.items(),key=lambda z:-z[1])[:4];total=sum(w for j,w in selected);q=[round(w/total*255) for j,w in selected];q[0]+=255-sum(q);skin.append(([j for j,w in selected],q));distances.append(neighbours[0][2])
if neckRepair:
    collarIds=[i for i,p in enumerate(points) if not headSurface[i] and 150<p.y<168 and abs(p.x)<14]
    if len(collarIds)<50:raise ValueError('Insufficient collar surface for neck clearance')
    collarTree=KDTree(len(collarIds))
    for i in collarIds:collarTree.insert(points[i],i)
    collarTree.balance()
    for i,blend in neckBlend.items():
        # The hidden neck follows the same skin field as its surrounding
        # collar, so head turns cannot pull it through a differently skinned
        # garment. Blend back to rigid head above the concealed region.
        neighbours=collarTree.find_n(points[i],3);total=sum(1/(distance+.2)**2 for _,_,distance in neighbours);matched={}
        for _,index,distance in neighbours:
            factor=1/(distance+.2)**2/total
            for j,w in zip(*skin[index]):matched[j]=matched.get(j,0)+factor*w/255
        original={j:w/255 for j,w in zip(*skin[i])};accum={j:w*(1-blend) for j,w in original.items()}
        for j,w in matched.items():accum[j]=accum.get(j,0)+w*blend
        selected=sorted(((j,w) for j,w in accum.items() if w>1e-6),key=lambda z:-z[1])[:4];total=sum(w for j,w in selected);q=[round(w/total*255) for j,w in selected];q[0]+=255-sum(q);skin[i]=([j for j,w in selected],q)
vertices=[];indices=[];joints=[];weights=[];lookup={};sourceMap=[]
for triangle in mesh.loop_triangles:
    for lid in triangle.loops:
        loop=mesh.loops[lid];i=loop.vertex_index;tex=uv.data[lid].uv;key=(i,round(tex.x,7),round(tex.y,7))
        if key not in lookup:
            js,ws=skin[i];point=Vector();normal=Vector();tangent=Vector()
            for j,w in zip(js,ws):
                point+=(fit[j]@points[i])*(w/255);normal+=(fit[j].to_3x3().inverted().transposed()@loop.normal)*(w/255);tangent+=(fit[j].to_3x3()@loop.tangent)*(w/255)
            lookup[key]=len(vertices);vertices.append(dict(position=point,normal=normal.normalized(),tangent=tangent.normalized(),uv=tuple(tex)));joints.extend(js+[0]*(4-len(js)));weights.extend(ws+[0]*(4-len(ws)));sourceMap.append(i)
        indices.append(lookup[key])
print('EXPORT COUNTS',len(points),len(vertices),len(indices),flush=True)
order=sorted({j for j,w in zip(joints,weights) if w});palette=b.Rx3(raw).get(0x0f3861a2)[0];nativeOrder=list(palette[272:272+palette[4]])
if set(order)!=set(nativeOrder):raise ValueError('Active bone set differs from native')
result,checked,checkedBind=b.build_rx3(raw,vertices,indices,joints,weights,order);rx=b.Rx3(result);next(s for s in rx.sections if s[0]==0x0f3861a2)[1]=palette
assert rx.get(0xdf9aec1e)==b.Rx3(raw).get(0xdf9aec1e)
dest=out/'package/data/sceneassets/slc';dest.mkdir(parents=True,exist_ok=True);(dest/f'specificmanager_{a.club_id}_0_0.rx3').write_bytes(rx.build())
report=dict(clubId=a.club_id,sourceHadRig=False,generatedNativeSkin=True,sourceVertices=len(points),exportVertices=len(vertices),triangles=len(indices)//3,nearestReferenceDistanceP99Cm=float(np.percentile(distances,99)),nativeBindUnchanged=True,nativeActiveBones=len(order),sourceSha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),runtimeValidated=False)
report.update(neckClearanceReviewed=bool(neckRepair),neckVerticesReviewed=len(neckBlend),maxNeckContractionCm=max(neckDisplacements.values(),default=0))
(out/'neck_clearance_vertices.json').write_text(json.dumps({str(i):dict(blend=w,contractionCm=neckDisplacements[i]) for i,w in neckBlend.items()}),encoding='utf8')
(out/'conversion.json').write_text(json.dumps(report,indent=2),encoding='utf8');(out/'source_vertex_map.json').write_text(json.dumps(sourceMap),encoding='utf8')
ob=bpy.data.objects.new('Odair editable source skin',mesh);bpy.context.scene.collection.objects.link(ob)
for i,(js,ws) in enumerate(skin):
    for j,w in zip(js,ws):
        name=f'native_{j:02d}';group=ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name);group.add([i],w/255,'REPLACE')
rigData=bpy.data.armatures.new('Native manager 31 bones');rig=bpy.data.objects.new('Generated native skeleton',rigData);bpy.context.scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
parents=[-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0]
for j in range(31):
    bone=rigData.edit_bones.new(f'native_{j:02d}');bone.head=source[j];child=next((i for i,p in enumerate(parents) if p==j and (source[i]-source[j]).length>1),None);bone.tail=source[child] if child is not None else source[j]+Vector((0,2,0))
    if parents[j]>=0:bone.parent=rigData.edit_bones[f'native_{parents[j]:02d}']
bpy.ops.object.mode_set(mode='OBJECT');modifier=ob.modifiers.new('Generated native weights','ARMATURE');modifier.object=rig
bpy.ops.wm.save_as_mainfile(filepath=str(out/'source_reviewed_weights.blend'));print(json.dumps(report,indent=2))
