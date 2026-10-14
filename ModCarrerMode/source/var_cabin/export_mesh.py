from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'source.blend'))
verts=[];indices=[];lookup={};height=200.0
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
floor=min(p.z for p in points);scale=height/(max(p.z for p in points)-floor)
for obj in objects:
 m=obj.data;m.calc_loop_triangles();m.calc_tangents(uvmap=m.uv_layers.active.name)
 nm=obj.matrix_world.to_3x3().inverted().transposed();tm=obj.matrix_world.to_3x3()
 def direction(p):return [float(p.x),float(p.z),float(-p.y)]
 for tri in m.loop_triangles:
  for li in tri.loops:
   loop=m.loops[li];p=obj.matrix_world@m.vertices[loop.vertex_index].co
   p=Vector((p.x,p.y,p.z-floor))*scale
   n=(nm@loop.normal).normalized();t=(tm@loop.tangent).normalized();uv=m.uv_layers.active.data[li].uv
   v=[direction(p),direction(n),direction(t),[float(uv.x),float(1-uv.y)]]
   key=tuple(round(x,7) for field in v for x in field)
   if key not in lookup:lookup[key]=len(verts);verts.append(v)
   indices.append(lookup[key])
assert len(verts)<65536
(R/'mesh_source.json').write_text(json.dumps({'vertices':verts,'indices':indices,'height_cm':height,'front_game_direction':[0,0,1]}),encoding='utf8')
print('exported',len(verts),'vertices',len(indices)//3,'triangles')
