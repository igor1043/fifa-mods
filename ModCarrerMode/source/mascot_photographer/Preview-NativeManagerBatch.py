"""Blender preview of vertices posed by the mod's actual native skin evaluator.

blender --background --python THIS_FILE -- --jobs preview-jobs.json --output DIR
The input contains three sampled native idle poses per manager, plus textures.
"""
import argparse,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector

def aim(obj,at):obj.rotation_euler=(Vector(at)-obj.location).to_track_quat('-Z','Y').to_euler()

def setup():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
 scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
 scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.19,.24,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
 scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast';scene.view_settings.exposure=.3
 for location,energy,size in [((-3,-4,5),550,4),((3,-1,3),300,3),((0,3,4),650,3)]:
  light=bpy.data.lights.new('Studio','AREA');light.energy=energy;light.shape='DISK';light.size=size;o=bpy.data.objects.new('Studio',light);scene.collection.objects.link(o);o.location=location;aim(o,(0,0,1))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.003));floor=bpy.context.object;mat=bpy.data.materials.new('Neutral floor');mat.diffuse_color=(.11,.14,.19,1);floor.data.materials.append(mat)
 camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';return scene,camera

def material(file,hair):
 mat=bpy.data.materials.new('Hair cutout' if hair else 'Opaque body');mat.use_nodes=True;nodes=mat.node_tree.nodes;bsdf=nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.75
 tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(file,check_existing=True);mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
 if hair:mat.node_tree.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha']);mat.surface_render_method='DITHERED'
 # Match native single-sided triangles. Cycles normally shows both sides,
 # which can conceal holes caused by wrong winding in the actual game.
 geometry=nodes.new('ShaderNodeNewGeometry');transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');mat.node_tree.links.new(geometry.outputs['Backfacing'],mix.inputs[0]);mat.node_tree.links.new(bsdf.outputs[0],mix.inputs[1]);mat.node_tree.links.new(transparent.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],nodes.get('Material Output').inputs['Surface'])
 return mat

def run(jobs,output,ids,body_only=False,head_only=False):
 output.mkdir(parents=True,exist_ok=True)
 for job in jobs:
  if ids and job['id'] not in ids:continue
  scene,camera=setup();objects=[];mats={}
  for pose,frame in enumerate(job['frames']):
   group=[]
   for part in frame['parts']:
    data=np.load(part['file']);v=data['positions'];xyz=np.c_[v[:,0],-v[:,2],v[:,1]]/100;tri=data['indices'].reshape(-1,3);mesh=bpy.data.meshes.new('Native posed surface');mesh.from_pydata(xyz.tolist(),[],tri.tolist());mesh.update();obj=bpy.data.objects.new(frame['name'],mesh);scene.collection.objects.link(obj);obj.location.x=(pose-1)*1.15
    uv=data['uvs'].copy();uv[:,1]=1-uv[:,1];layer=mesh.uv_layers.new();layer.data.foreach_set('uv',uv[tri.reshape(-1)].reshape(-1));mesh.polygons.foreach_set('use_smooth',np.ones(len(tri),dtype=bool));n=data['normals'];mesh.normals_split_custom_set_from_vertices(np.c_[n[:,0],-n[:,2],n[:,1]].tolist())
    key=(part['texture'],part['hair'])
    if key not in mats:mats[key]=material(job['textures'][part['texture']],part['hair'])
    mesh.materials.append(mats[key]);group.append(obj)
   objects.append(group)
  if not head_only:
   camera.location=(0,-8,2.6);aim(camera,(0,0,.96));camera.data.ortho_scale=3.75;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.filepath=str(output/f'{job["id"]}-poses.png');bpy.ops.render.render(write_still=True)
  for group in objects[1:]:
   for obj in group:obj.hide_render=True
  if not body_only:
   camera.location=(-.63,-2.2,1.87);aim(camera,(-1.15,0,1.69));camera.data.ortho_scale=.65;scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.filepath=str(output/f'{job["id"]}-head.png');bpy.ops.render.render(write_still=True)
  print('NATIVE_MANAGER_PREVIEW',job['id'],job['name'],flush=True)
  for block in (bpy.data.meshes,bpy.data.materials,bpy.data.images):
   for item in list(block):
    if item.users==0:block.remove(item)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--jobs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ids',type=int,nargs='*');p.add_argument('--body-only',action='store_true');p.add_argument('--head-only',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);run(json.loads(a.jobs.read_text(encoding='utf8')),a.output,a.ids,a.body_only,a.head_only)
