from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
p=json.loads((R/'converted_mesh.json').read_text(encoding='utf8'));v=p['positions'];ids=p['indices']
classes=json.loads((R/'mesh_source.json').read_text(encoding='utf8'))['triangle_materials']
verts=[(v[i]/100,-v[i+2]/100,v[i+1]/100) for i in range(0,len(v),3)]
mesh=bpy.data.meshes.new('RX3 relido');mesh.from_pydata(verts,[],[ids[i:i+3] for i in range(0,len(ids),3)]);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for l in mesh.loops:uv.data[l.index].uv=(p['uvs'][2*l.vertex_index],1-p['uvs'][2*l.vertex_index+1])
n=p['normals'];mesh.normals_split_custom_set_from_vertices([(n[i],-n[i+2],n[i+1]) for i in range(0,len(n),3)])
o=bpy.data.objects.new('Cabine VAR modelo 2 — RX3',mesh);bpy.context.scene.collection.objects.link(o)
for name,roughness,metal in [('body',.6,0),('frame',.35,.2),('mirror',.12,.8)]:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=roughness;bs.inputs['Metallic'].default_value=metal
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'colour_rx3.png'),check_existing=True)
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(mat)
for face,kind in zip(mesh.polygons,classes):face.material_index=['body','frame','mirror'].index(kind if kind in ('frame','mirror') else 'body');face.use_smooth=kind!='mirror'
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.4,.45,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.01));ground=bpy.context.object
mat=bpy.data.materials.new('Grama de prévia');mat.diffuse_color=(.035,.11,.035,1);ground.data.materials.append(mat)
bpy.ops.object.light_add(type='AREA',location=(4,-6,8));bpy.context.object.data.energy=1200;bpy.context.object.data.size=6
bpy.ops.object.light_add(type='AREA',location=(-3,3,4));bpy.context.object.data.energy=500;bpy.context.object.data.size=5
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.9
for i,location in enumerate([(2,-4,2.8),(-2,4,2.8)]):
    cam.location=location;cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(R/f'cabine_var2_rx3_{i}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'cabine_var2_rx3.blend'))
