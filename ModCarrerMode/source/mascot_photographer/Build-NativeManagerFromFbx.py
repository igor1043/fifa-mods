"""Convert a profiled FBX manager to the native FIFA 16 31-bone palette.

Requires an explicit source joint profile and optional UV chart relocations.
Retargets complete authored skins by semantic joint. Partial or missing skins
are completed from a native manager fitted to the measured source rest pose.
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
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=a.source,use_custom_normals=True)
candidates=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and len(obj.data.vertices)]
sourceObject=next((obj for obj in candidates if obj.name.startswith('slc_mat:')),max(candidates,key=lambda obj:len(obj.data.polygons)))
sourceMesh=sourceObject.data;sourceUv=sourceMesh.uv_layers.active
if sourceUv is None:raise ValueError('Source FBX has no UVs')
points=[];faces=[];faceuv=[];authored=[]
for v in sourceMesh.vertices:
    q=sourceObject.matrix_world@v.co;unit=profile.get('unitCorrection',1)*100;points.append(Vector((q.x*unit,q.z*unit,-q.y*unit)))
    authored.append({sourceObject.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-6})
for poly in sourceMesh.polygons:
    faces.append(list(poly.vertices));faceuv.extend([tuple(sourceUv.data[i].uv) for i in poly.loop_indices])
originalUnweighted=sum(not weights for weights in authored)
fullAuthoredSkin=len({name for row in authored for name in row})>=20 and originalUnweighted==0 and not profile.get('regenerateSkin',False)
headHeight=profile['sourceJointsCm']['14'][1]
headRigidHeight=headHeight+.5
headSurface=[False]*len(points);at=0
for face in faces:
    for i in face:
        if (points[i].y>headHeight-18 and faceuv[at][0]>.666 and faceuv[at][1]>.666) or points[i].y>headRigidHeight or (points[i].y>headHeight-3 and authored[i].get('Head',0)>.5):headSurface[i]=True
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
mesh=bpy.data.meshes.new('Updated FBX with supplied UV charts');mesh.from_pydata([tuple(v) for v in points],[],faces);mesh.update();uv=mesh.uv_layers.new()
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
    # Retain reviewed authored torso weights, with a spatial feather into
    # inferred shoulder/limb skin. The FBX has no arm or leg clusters.
    mapping={'Hips':2,'Spine':11,'Spine2':12,'Spine3':12,'Neck':13,'Neck1':13,'Head':14}
    known={}
    for name,w in authored[sourceIndex].items():
        if name in mapping:known[mapping[name]]=known.get(mapping[name],0)+w
    lower=max(0,min(1,(point.y-96)/12));lateral=max(0,min(1,(26-abs(point.x))/10))
    alpha=profile.get('authoredTorsoBlend',.65)*lower*lower*(3-2*lower)*lateral*lateral*(3-2*lateral)
    if known and alpha>0:
        total=sum(accum.values());kt=sum(known.values());accum={j:w/total*(1-alpha) for j,w in accum.items()}
        for j,w in known.items():accum[j]=accum.get(j,0)+w/kt*alpha
    if fullAuthoredSkin:
        semantic={'Hips':2,'Spine':11,'Spine1':12,'Spine2':12,'Spine3':12,'Neck':13,'Neck1':13,'Head':14,'HeadEnd':14,
                  'LeftShoulder':16,'LeftArm':17,'LeftForeArm':18,'LeftHand':19,
                  'RightShoulder':21,'RightArm':22,'RightForeArm':23,'RightHand':24,
                  'RightUpLeg':3,'RightLeg':4,'RightFoot':5,'RightFootEnd':5,
                  'LeftUpLeg':7,'LeftLeg':8,'LeftFoot':9,'LeftFootEnd':9}
        mapped={}
        for name,w in authored[sourceIndex].items():
            j=semantic.get(name)
            if j is None and name.startswith('LeftHand'):j=19
            if j is None and name.startswith('RightHand'):j=24
            if j is not None:mapped[j]=mapped.get(j,0)+w
        if not mapped:raise ValueError('Authored skin contains no supported semantic joints')
        accum=mapped
    if point.y>headHeight-10:
        if headSurface[sourceIndex] and point.y>headHeight-6:accum={14:1}
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
    if (not fullAuthoredSkin or profile.get('reviewAxilla',False)) and abs(point.x)>14 and 115<point.y<157:
        # Continuous anatomical shoulder/axilla blend, rather than a hard
        # X cutoff that makes a visible flap at the sleeve-to-torso seam.
        chain=(16,17,18,19) if point.x>0 else (21,22,23,24)
        arm={j:w for j,w in accum.items() if j in chain};body={j:w for j,w in accum.items() if j in (2,11,12,13)}
        if not arm:arm={17 if point.x>0 else 22:1}
        if not body:body={12 if point.y>126 else 11:1}
        inner=profile.get('axillaInnerX',14)+max(0,profile.get('axillaReferenceHeight',146)-point.y)*profile.get('axillaSlope',.48)
        t=max(0,min(1,(abs(point.x)-inner)/profile.get('axillaBlendWidth',12)));mass=t*t*(3-2*t)
        if profile.get('axillaRigidUpperArm',False) and abs(point.x)<34:
            arm={17 if point.x>0 else 22:1};body={12 if point.y>126 else 11:1}
        armTotal=sum(arm.values());bodyTotal=sum(body.values())
        accum={j:w/armTotal*mass for j,w in arm.items()}
        accum.update({j:w/bodyTotal*(1-mass) for j,w in body.items()})
    if point.y<90 and abs(point.x)>5:
        opposite=(3,4,5) if point.x>0 else (7,8,9);accum={j:w for j,w in accum.items() if j not in opposite}
    if profile.get('capsuleArms',False) and abs(point.x)>7 and 80<point.y<160:
        chain=(16,17,18,19) if point.x>0 else (21,22,23,24)
        def segment_distance(p,start,end):
            axis=end-start;t=max(0,min(1,(p-start).dot(axis)/axis.length_squared));return (p-(start+axis*t)).length
        distancesToBones=[segment_distance(point,source[j],source[j+1]) for j in chain]
        def fade(lo,hi,value):
            t=max(0,min(1,(value-lo)/(hi-lo)));return t*t*(3-2*t)
        masses=[(1-fade(4,8,distancesToBones[0]))*fade(7,17,abs(point.x)),1-fade(7,12,distancesToBones[1]),1-fade(5,9,distancesToBones[2]),1-fade(4,8,distancesToBones[3])]
        mass=max(masses)
        if abs(point.x)>40:mass=1
        body={j:w for j,w in accum.items() if j not in (16,17,18,19,21,22,23,24) and w>1e-9} or {12 if point.y>126 else 11:1}
        total=sum(body.values());arm={j:1/(distance+2)**4 for j,distance in zip(chain,distancesToBones)}
        if abs(point.x)>45 and point.y<source[chain[-1]].y-3:arm={chain[-1]:1}
        armTotal=sum(arm.values());accum={j:w/total*(1-mass) for j,w in body.items()}
        for j,w in arm.items():accum[j]=w/armTotal*mass
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
assert all(sum(w for j,w in zip(*skin[i]) if j==14)==255 for i,p in enumerate(points) if p.y>headRigidHeight), 'Upper head must remain rigid with face, hair and glasses'
garmentVertices=0
if profile.get('reviewGarment',False):
    def eased(lo,hi,x):
        t=max(0,min(1,(x-lo)/(hi-lo)));return t*t*(3-2*t)
    hip=source[2].y;chest=source[12].y
    for i,p in enumerate(points):
        upperFade=profile.get('garmentUpperFade',[chest-4,chest+4])
        alpha=(1-eased(23,28,abs(p.x)))*eased(hip-10,hip-5,p.y)*(1-eased(*upperFade,p.y))
        if alpha<=.001:continue
        # Give all layers of the waistband the same continuous axial skin
        # field. Per-vertex left/right mixtures made the hem ripple even
        # though those coincident vertices belong to one piece of fabric.
        spine=eased(hip+3,source[11].y+9,p.y);upper=eased(source[11].y+9,chest+4,p.y)
        target={2:1-spine,11:spine*(1-upper),12:spine*upper}
        field={j:w/255*(1-alpha) for j,w in zip(*skin[i])}
        for j,w in target.items():field[j]=field.get(j,0)+w*alpha
        selected=sorted(field.items(),key=lambda z:-z[1])[:4];total=sum(w for j,w in selected);ws=[round(w/total*255) for j,w in selected];ws[0]+=255-sum(ws);skin[i]=([j for j,w in selected],ws);garmentVertices+=1
passes=profile.get('shoulderSmoothingPasses',0)
if passes:
    # Smooth the shoulder skin over mesh edges, including coincident UV seam
    # vertices. Keep the exposed head and extremities outside this repair.
    rows=[];columns=[];coincident={}
    for face in faces:
        for i,j in zip(face,face[1:]+face[:1]):rows.extend((i,j));columns.extend((j,i))
    for i,p in enumerate(points):
        key=tuple(round(x,3) for x in p)
        if key in coincident:rows.extend((i,coincident[key]));columns.extend((coincident[key],i))
        else:coincident[key]=i
    rows=np.array(rows);columns=np.array(columns);counts=np.bincount(rows,minlength=len(points));field=np.zeros((len(points),31))
    for i,(js,ws) in enumerate(skin):
        for j,w in zip(js,ws):field[i,j]=w/255
    mask=np.array([110<p.y<157 and abs(p.x)>10 for p in points])&(counts>0)
    for iteration in range(passes):
        sums=np.zeros_like(field);np.add.at(sums,rows,field[columns]);average=sums/np.maximum(counts[:,None],1);field[mask]=field[mask]*.45+average[mask]*.55
    for i in np.where(mask)[0]:
        js=np.argsort(-field[i])[:4];values=field[i,js];ws=np.rint(values/values.sum()*255).astype(int);ws[0]+=255-ws.sum();skin[i]=(js.tolist(),ws.tolist())
sealedVertices=0
if profile.get('sealSkinSeams',False):
    groups={}
    for i,p in enumerate(points):groups.setdefault(tuple(round(x,3) for x in p),[]).append(i)
    for ids in groups.values():
        if len(ids)<2:continue
        field={};position=sum((points[i] for i in ids),Vector())/len(ids)
        for i in ids:
            for j,w in zip(*skin[i]):field[j]=field.get(j,0)+w/len(ids)
        selected=sorted(field.items(),key=lambda z:-z[1])[:4];total=sum(w for j,w in selected);ws=[round(w/total*255) for j,w in selected];ws[0]+=255-sum(ws);js=[j for j,w in selected]
        if position.y>headRigidHeight:js,ws=[14],[255]
        for i in ids:points[i]=position.copy();skin[i]=(js.copy(),ws.copy())
        sealedVertices+=len(ids)
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
report=dict(clubId=a.club_id,sourceHadRig=profile['sourceHadRig'],sourceBones=profile['sourceOriginalBones'],fullAuthoredSkinRetargeted=fullAuthoredSkin,originalUnweightedVertices=originalUnweighted,authoredTorsoWeightsAdapted=bool(any(authored)),missingLimbWeightsGenerated=not fullAuthoredSkin,generatedNativeSkin=True,sourceVertices=len(points),exportVertices=len(vertices),triangles=len(indices)//3,nearestReferenceDistanceP99Cm=float(np.percentile(distances,99)),nativeBindUnchanged=True,nativeActiveBones=len(order),sourceSha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),runtimeValidated=False)
report.update(neckClearanceReviewed=bool(neckRepair),neckVerticesReviewed=len(neckBlend),maxNeckContractionCm=max(neckDisplacements.values(),default=0),shoulderSmoothingPasses=passes,garmentTransitionVertices=garmentVertices,sealedSkinSeamVertices=sealedVertices)
(out/'neck_clearance_vertices.json').write_text(json.dumps({str(i):dict(blend=w,contractionCm=neckDisplacements[i]) for i,w in neckBlend.items()}),encoding='utf8')
(out/'conversion.json').write_text(json.dumps(report,indent=2),encoding='utf8');(out/'source_vertex_map.json').write_text(json.dumps(sourceMap),encoding='utf8')
ob=bpy.data.objects.new('Manager FBX reviewed skin',mesh);bpy.context.scene.collection.objects.link(ob)
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
