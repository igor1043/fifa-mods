"""Create a real, editable 11-armature Blender project outside FIFA."""
from pathlib import Path
import sys,json,math
import bpy,numpy as np
from mathutils import Matrix,Vector
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from rig_io import read_rig,skin
manifest=json.loads((root/'assets/scene.json').read_text(encoding='utf8'))
texture_map=json.loads((root/'texture-map.json').read_text(encoding='utf8'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
C=Matrix.Rotation(math.pi/2,4,'X');Ci=C.inverted()
def matrix(values):
 M=C@Matrix(np.array(values).reshape(4,4).T.tolist())@Ci
 M.translation*=.01
 for i in range(3):
  col=M.col[i].to_3d().normalized()
  for j in range(3):M[j][i]=col[j]
 return M
materials={};images={};arms=[];geometry=[]
for info in manifest['variants'][0]['players']:
 ident=info['id'];rig=read_rig(root/'assets'/f'player-{ident}.ff3d')
 bpy.ops.object.select_all(action='DESELECT')
 data=bpy.data.armatures.new('FIFA_400_'+str(ident));arm=bpy.data.objects.new(info['name']+' · esqueleto',data);bpy.context.collection.objects.link(arm)
 bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
 for i,bone in enumerate(rig['bones']):
  eb=data.edit_bones.new(bone['name']);M=matrix(bone['rest'].T.ravel())
  eb.head=M.translation;eb.tail=eb.head+M.to_3x3().col[1].normalized()*.035;eb.matrix=M;eb.length=.035
  if bone['parent']>=0:eb.parent=data.edit_bones[bone['parent']]
 bpy.ops.object.mode_set(mode='OBJECT');arm.show_in_front=True;data.display_type='STICK'
 arm.location=(info['position'][0]*.01,-info['position'][2]*.01,0)
 arm['player_id']=ident;arm['source']='FIFA 16 skeleton, eight skin influences';arm['editing']='Frame 1: original. Frame 2: proposed arm adjustment.'
 for part_no,part in enumerate(rig['parts']):
  v=part['v'];p=v['p']*.01;vertices=np.c_[p[:,0],-p[:,2],p[:,1]]
  mesh=bpy.data.meshes.new(f'{ident}_{part_no}');mesh.from_pydata(vertices.tolist(),[],part['idx'].reshape(-1,3).tolist());mesh.update()
  uv=mesh.uv_layers.new(name='FIFA UV')
  uvcoords=v['uv'][np.array([l.vertex_index for l in mesh.loops],dtype=np.int32)].copy();uvcoords[:,1]=1-uvcoords[:,1];uv.data.foreach_set('uv',uvcoords.ravel())
  obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj);obj.parent=arm
  for polygon in mesh.polygons:polygon.use_smooth=True
  for b in rig['bones']:obj.vertex_groups.new(name=b['name'])
  joints=v['j'];weights=v['w'];totals=weights.sum(axis=1)
  for slot in range(8):
   valid=weights[:,slot]>0
   for joint in np.unique(joints[valid,slot]):
    ids=np.flatnonzero(valid&(joints[:,slot]==joint));values=weights[ids,slot]/totals[ids]
    for weight in np.unique(values):obj.vertex_groups[int(joint)].add(ids[values==weight].tolist(),float(weight),'ADD')
  modifier=obj.modifiers.new('FIFA skeleton · 8 influences','ARMATURE');modifier.object=arm;modifier.use_deform_preserve_volume=False
  key=(ident,part['texture'],tuple(part['tint']),tuple(part['color']),part['blend'],part['alpha'])
  if key not in materials:
   mat=bpy.data.materials.new(f'FIFA_{ident}_{part_no}');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.83
   if part['texture']>=0:
    path=root/texture_map[str(ident)][part['texture']]
    if str(path) not in images:images[str(path)]=bpy.data.images.load(str(path))
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=images[str(path)]
    mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*part['tint'],1)
    mat.node_tree.links.new(tex.outputs['Color'],mix.inputs[1]);mat.node_tree.links.new(mix.outputs['Color'],bs.inputs['Base Color'])
    if part['blend'] or '/hair/' in part['asset']:
     mat.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha']);mat.surface_render_method='DITHERED'
   else:bs.inputs['Base Color'].default_value=(*part['color'],1)
   materials[key]=mat
  obj.data.materials.append(materials[key]);geometry.append((obj,ident,part_no))
 for frame,variant in enumerate(manifest['variants'],1):
  posed=next(p for p in variant['players'] if p['id']==ident)
  worlds=[matrix(values) for values in posed['poseWorld']]
  for i,values in enumerate(posed['poseWorld']):
   pb=arm.pose.bones[i];pb.rotation_mode='QUATERNION';parent=rig['bones'][i]['parent'];bone=arm.data.bones[i]
   kwargs={} if parent<0 else dict(parent_matrix=worlds[parent],parent_matrix_local=arm.data.bones[parent].matrix_local)
   pb.matrix_basis=bone.convert_local_to_pose(worlds[i],bone.matrix_local,invert=True,**kwargs)
   for key in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=key,frame=frame,group=pb.name)
 arms.append(arm)
 print('BLENDER_RIG',ident,len(data.bones),flush=True)
# Editable native rigs plus an ordinary studio floor and real area lights.
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='Piso de estudo · fora do FIFA'
mat=bpy.data.materials.new('Piso neutro');mat.diffuse_color=(.17,.21,.22,1);mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.17,.21,.22,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=1;floor.data.materials.append(mat);floor.location.z=-.01
def area(name,position,power,size):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=position;o.rotation_euler=(Vector((0,0,.9))-o.location).to_track_quat('-Z','Y').to_euler()
area('Luz principal',(-3,-4,6),750,5);area('Preenchimento',(4,-1,4),420,4);area('Recorte',(0,3,5),600,3)
world=scene.world or bpy.data.worlds.new('Estúdio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.16,.20,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45
bpy.ops.object.camera_add(location=(0,-7,2.2));camera=bpy.context.object;camera.name='Câmera · fotografia dos 11';camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=4.1;scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.frame_start=1;scene.frame_end=2
scene.timeline_markers.new('POSE ATUAL',frame=1);scene.timeline_markers.new('AJUSTE DE BRAÇOS',frame=2)
scene.frame_set(2)
bpy.ops.object.select_all(action='DESELECT');active=arms[6];active.select_set(True);bpy.context.view_layer.objects.active=active
# Store useful arm selection in every real FIFA armature.
for arm in arms:
 for bone in arm.data.bones:bone.select=bone.name in ('LeftArm','RightArm','LeftForeArm','RightForeArm','LeftHand','RightHand')
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_floor=False
text=bpy.data.texts.new('LEIA-ME · braços')
text.write('Cena isolada: não modifica o jogo.\nQuadro 1: pose atual. Quadro 2: proposta, apenas braços.\nSelecione um esqueleto, entre em Pose Mode e ajuste LeftArm/RightArm, ForeArm e Hand.\nCada jogador conserva os 400 ossos e oito influências FIFA por vértice.\nUse a bancada web para ajustes simples e exportação de JSON.\nRenderização do Blender é uma referência de pose; não reproduz a iluminação final do FIFA.\n')
for image in images.values():image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'Flamengo-onze-editavel.blend'))
for frame,label in ((1,'pose-atual'),(2,'bracos-naturais')):
 scene.frame_set(frame);scene.render.filepath=str(root/(label+'.png'));bpy.ops.render.render(write_still=True)
print('BLENDER_OFFLINE_COMPLETE',flush=True)
