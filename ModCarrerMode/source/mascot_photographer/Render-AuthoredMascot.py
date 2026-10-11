"""Render the provided FBX and three poses skinned from the final RX3 package."""
from pathlib import Path
import sys,json,bpy,importlib.util
from mathutils import Vector
import argparse
parser=argparse.ArgumentParser(description="Preview source FBX and final FIFA RX3 poses")
parser.add_argument('--source',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--tools',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
root=Path(args.output);tools=Path(args.tools)
spec=importlib.util.spec_from_file_location('builder',tools/'Build-MascotFromFbx.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
for club in [{'folder': '.'}]:
 folder=root;src=Path(args.source)
 vertices,indices,_,_=builder.load_source_mesh(next(src.glob('*.fbx')))
 original={'positions':[list(v['position']) for v in vertices],'uvs':[list(v['uv']) for v in vertices],'indices':indices}
 (folder/'source_reference.json').write_text(json.dumps(original),encoding='utf8')
 original_floor=min(v['position'].y for v in vertices);scale=180/(max(v['position'].y for v in vertices)-original_floor)
 original_xyz=[[v['position'].x*scale,(v['position'].y-original_floor)*scale,v['position'].z*scale] for v in vertices]
 part=json.loads((folder/'converted_mesh.json').read_text())['parts'][0];poses=json.loads((folder/'poses.json').read_text())
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.resolution_x=480;scene.render.resolution_y=600;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.08,.09,.12,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.view_settings.view_transform='Standard'
 for loc,power in [((-3,-4,5),500),((3,-2,3),400)]:
  light=bpy.data.lights.new('Area','AREA');light.energy=power;light.size=4;ob=bpy.data.objects.new('Area',light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1.2))-ob.location).to_track_quat('-Z','Y').to_euler()
 camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);camdata.type='ORTHO';camdata.ortho_scale=2.25;scene.camera=cam
 cam.location=(0,-5,.90);cam.rotation_euler=(Vector((0,0,.90))-cam.location).to_track_quat('-Z','Y').to_euler()
 textures={'original':next(p for p in src.rglob('*') if p.is_file() and ('basecolor' in p.name.lower() or 'tripo_rgb' in p.name.lower())),'converted':folder/'exported_basecolor.png'}
 for label in ['original','idle0.5','walk0.5','cheer0.5']:
  prev=bpy.data.objects.get('Mascot preview')
  if prev:bpy.data.objects.remove(prev,do_unlink=True)
  xyz=original_xyz if label=='original' else poses[label];ind=indices if label=='original' else part['indices']
  mesh=bpy.data.meshes.new(label);mesh.from_pydata([(v[0]/100,-v[2]/100,v[1]/100) for v in xyz],[],[ind[i:i+3] for i in range(0,len(ind),3)]);mesh.update();ob=bpy.data.objects.new('Mascot preview',mesh);scene.collection.objects.link(ob)
  uv=mesh.uv_layers.new()
  for loop in mesh.loops:
   i=loop.vertex_index;uv.data[loop.index].uv=original['uvs'][i] if label=='original' else (part['uvs'][2*i],1-part['uvs'][2*i+1])
  for poly in mesh.polygons:poly.use_smooth=True
  mat=bpy.data.materials.new(label);mat.use_nodes=True;node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(textures['original' if label=='original' else 'converted']));bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.75;mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(mat)
  scene.render.filepath=str(folder/(label+'.png'));bpy.ops.render.render(write_still=True)
 print('RENDERED',club['folder'],flush=True)
print('ALL RENDERS COMPLETE',flush=True)
