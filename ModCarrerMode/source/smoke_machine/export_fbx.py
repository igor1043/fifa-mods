from pathlib import Path
import bpy,json,sys
from mathutils import Vector
R=Path(__file__).resolve().parent
S=Path('C:/Users/igorv/OneDrive/\u00c1rea de Trabalho/maquina fuma\u00e7a')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(S/'industrial+machine+3d+model.fbx'))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'source_full.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
assert points
lo=[min(p[i] for p in points) for i in range(3)]
hi=[max(p[i] for p in points) for i in range(3)]
height=55.0
scale=height/(hi[2]-lo[2])
center=Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]))
verts=[];indices=[];lookup={}
for obj in objects:
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('FIFA triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    modifier=obj.modifiers.new('Broadcast distance geometry','DECIMATE')
    modifier.ratio=.12
    modifier.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    m=obj.data;m.calc_loop_triangles()
    assert m.uv_layers.active,obj.name
    m.calc_tangents(uvmap=m.uv_layers.active.name)
    nm=obj.matrix_world.to_3x3().inverted().transposed();tm=obj.matrix_world.to_3x3()
    def direction(p):return [float(p.x),float(p.z),float(-p.y)]
    for tri in m.loop_triangles:
        for li in tri.loops:
            loop=m.loops[li]
            p=(obj.matrix_world@m.vertices[loop.vertex_index].co-center)*scale
            n=(nm@loop.normal).normalized();t=(tm@loop.tangent).normalized();uv=m.uv_layers.active.data[li].uv
            v=[direction(p),direction(n),direction(t),[float(uv.x),float(1-uv.y)]]
            key=tuple(round(x,7) for field in v for x in field)
            if key not in lookup:lookup[key]=len(verts);verts.append(v)
            indices.append(lookup[key])
assert len(verts)<65536
report={'source':str(S),'vertices':verts,'indices':indices,'height_cm':height,
        'source_bounds': [lo,hi],'meshes':[{'name':o.name,'vertices':len(o.data.vertices),'materials':[x.name for x in o.data.materials]} for o in objects]}
(R/'mesh_source.json').write_text(json.dumps(report),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'source.blend'))
print('Exported',len(verts),'vertices',len(indices)//3,'triangles; bounds',lo,hi)
