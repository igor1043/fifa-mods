"""Preview from the RX3 decoded geometry and decoded diffuse, not the source FBX."""
from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
p=json.loads((R/'converted_mesh.json').read_text());v=p['positions'];ids=p['indices']
verts=[(v[i]/100,-v[i+2]/100,v[i+1]/100) for i in range(0,len(v),3)]
mesh=bpy.data.meshes.new('FIFA RX3');mesh.from_pydata(verts,[],[ids[i:i+3] for i in range(0,len(ids),3)]);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for l in mesh.loops:uv.data[l.index].uv=(p['uvs'][2*l.vertex_index],1-p['uvs'][2*l.vertex_index+1])
n=p['normals'];mesh.normals_split_custom_set_from_vertices([(n[i],-n[i+2],n[i+1]) for i in range(0,len(n),3)])
o=bpy.data.objects.new('Smoke machine — decoded RX3',mesh);bpy.context.scene.collection.objects.link(o)
mat=bpy.data.materials.new('Supplied finish');mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.55;bs.inputs['Metallic'].default_value=.15
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'colour_rx3.png'))
mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(mat)
for face in mesh.polygons:face.use_smooth=True
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=900;s.render.resolution_y=800;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.37,.42,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.01));ground=bpy.context.object
mat=bpy.data.materials.new('Grass preview');mat.diffuse_color=(.025,.09,.025,1);ground.data.materials.append(mat)
bpy.ops.object.light_add(type='AREA',location=(2,-3,4));bpy.context.object.data.energy=500;bpy.context.object.data.size=3
bpy.ops.object.light_add(type='AREA',location=(-2,3,2));bpy.context.object.data.energy=200;bpy.context.object.data.size=3
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.85
for i,location in enumerate([(1.5,-2,1.3),(-1.5,2,1.3)]):
    cam.location=location;cam.rotation_euler=(Vector((0,0,.27))-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(R/f'smoke_machine_rx3_{i}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'converted_preview.blend'))
