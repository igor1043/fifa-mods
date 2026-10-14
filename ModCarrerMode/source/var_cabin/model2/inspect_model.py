from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent
S=Path('C:/Users/igorv/OneDrive/\u00c1rea de Trabalho/CABINE DO VAR 2')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=str(S/'Cabine do Var.obj'),forward_axis='NEGATIVE_Z',up_axis='Y')
objects=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    m=o.data;m.calc_loop_triangles()
    ps=[o.matrix_world@v.co for v in m.vertices]
    materials=[]
    for i,mat in enumerate(m.materials):
        faces=[p for p in m.polygons if p.material_index==i]
        points=[o.matrix_world@m.vertices[v].co for p in faces for v in p.vertices]
        uvs=[tuple(m.uv_layers.active.data[l].uv) for p in faces for l in p.loop_indices]
        materials.append({'index':i,'name':mat.name,'faces':len(faces),'triangles':sum(t.material_index==i for t in m.loop_triangles),'bounds':[[min(p[a] for p in points) for a in range(3)],[max(p[a] for p in points) for a in range(3)]],'uv_bounds':[[min(p[a] for p in uvs) for a in range(2)],[max(p[a] for p in uvs) for a in range(2)]]})
        mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
        bs=nodes.get('Principled BSDF')
        for node in list(nodes):
            if node.type=='TEX_IMAGE':nodes.remove(node)
        if i==0:
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(S/'CABINE+DO+VAR_basecolor.jpg'))
            links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.62
            normal=nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(S/'CABINE+DO+VAR_normal.png'));normal.image.colorspace_settings.name='Non-Color'
            nm=nodes.new('ShaderNodeNormalMap');links.new(normal.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:
            bs.inputs['Base Color'].default_value=(.42,.49,.56,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.12
    objects.append({'name':o.name,'vertices':len(ps),'triangles':len(m.loop_triangles),'bounds':[[min(p[a] for p in ps) for a in range(3)],[max(p[a] for p in ps) for a in range(3)]],'materials':materials,'uvs':[u.name for u in m.uv_layers]})
(R/'source_analysis.json').write_text(json.dumps({'objects':objects,'source':str(S/'Cabine do Var.obj')},indent=2),encoding='utf8')
print(json.dumps(objects,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'source.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.5,.5,1)
allps=[o.matrix_world@v.co for o in s.objects if o.type=='MESH' for v in o.data.vertices]
lo=Vector(tuple(min(p[a] for p in allps) for a in range(3)));hi=Vector(tuple(max(p[a] for p in allps) for a in range(3)))
center=(lo+hi)/2;span=max(hi-lo)
bpy.ops.object.light_add(type='AREA',location=center+Vector((2,-3,4))*span);bpy.context.object.data.energy=450;bpy.context.object.data.size=4*span
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.4
for i,p in enumerate([(1.6,-2.5,1.0),(-1.6,2.5,1.0)]):
    cam.location=center+Vector(p)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(R/f'source_view_{i}.png');bpy.ops.render.render(write_still=True)
