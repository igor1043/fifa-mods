from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'repaired.blend'))
verts=[];indices=[];lookup={};height=200.0;classes=[]
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
floor=min(p.z for p in points);scale=height/(max(p.z for p in points)-floor)
counts={'body':0,'frame':0,'mirror':0,'cabinet':0,'screen':0,'black':0}
for obj in objects:
    m=obj.data;m.calc_loop_triangles();m.calc_tangents(uvmap=m.uv_layers.active.name)
    nm=obj.matrix_world.to_3x3().inverted().transposed();tm=obj.matrix_world.to_3x3()
    def direction(p):return [float(p.x),float(p.z),float(-p.y)]
    for tri in m.loop_triangles:
        center=sum((obj.matrix_world@m.vertices[i].co for i in tri.vertices),Vector())/3
        face_normal=(nm@tri.normal).normalized()
        material='mirror' if tri.material_index==1 else ('frame' if (abs(center.x)>.248 or center.y>.23 or center.z>.82) and center.z>.075 else 'body')
        if material=='body':
            if abs(center.x)<.148 and -.12<center.y<.16 and .025<center.z<.555:
                material='black' if face_normal.z>.45 and center.z>.50 else 'cabinet'
            elif abs(center.x)<.23 and -.04<center.y<.18 and .545<center.z<.77:
                material='screen' if face_normal.y<-.8 and -.206<center.x<.206 and .56<center.z<.718 else 'black'
        counts[material]+=1;classes.append(material)
        for li in tri.loops:
            loop=m.loops[li];raw=obj.matrix_world@m.vertices[loop.vertex_index].co
            p=Vector((raw.x,raw.y,raw.z-floor))*scale
            n=(nm@(tri.normal if material=='mirror' else loop.normal)).normalized();t=(tm@loop.tangent).normalized();uv=m.uv_layers.active.data[li].uv
            # Separate utility cells avoid reusing body logos on new glass UVs.
            if material=='body':mapped=[max(0,min(1,float(uv.x))),max(0,min(.5,float(1-uv.y)*.5))]
            elif material=='frame':mapped=[.125,.625]
            elif material=='mirror':mapped=[.75,.625]
            elif material=='black':mapped=[.375,.5625]
            elif material=='screen':
                u=max(0,min(1,(raw.x+.206)/.412));v=max(0,min(1,(raw.z-.56)/.158))
                mapped=[(317+(1-u)*367)/2048,(686+v*180)/4096]
            else:
                if abs(face_normal.y)>.55:u=(raw.x+.128)/.256
                elif abs(face_normal.x)>.55:u=(raw.y+.10)/.23 if face_normal.x>0 else (.13-raw.y)/.23
                else:u=.5
                u=max(0,min(1,u));v=max(0,min(1,(raw.z-.028)/.51))
                mapped=[(12+u*225)/2048,(174+(1-v)*526)/4096]
            v=[direction(p),direction(n),direction(t),mapped]
            key=tuple(round(x,7) for field in v for x in field)
            if key not in lookup:lookup[key]=len(verts);verts.append(v)
            indices.append(lookup[key])
assert len(verts)<65536 and counts['mirror']==48
# Recompute the tangent basis after the planar/atlas UV changes.
tangents=[Vector() for _ in verts]
for a,b,c in zip(indices[0::3],indices[1::3],indices[2::3]):
    p0,p1,p2=(Vector(verts[i][0]) for i in (a,b,c));q0,q1,q2=(Vector(verts[i][3]) for i in (a,b,c))
    du=q1-q0;dv=q2-q0;den=du.x*dv.y-du.y*dv.x
    direction=(dv.y*(p1-p0)-du.y*(p2-p0))/den if abs(den)>1e-12 else Vector((1,0,0))
    for i in (a,b,c):
        n=Vector(verts[i][1]);t=direction-n*n.dot(direction)
        if t.length_squared<1e-12:t=n.cross(Vector((0,0,1)))
        if t.length_squared<1e-12:t=n.cross(Vector((0,1,0)))
        tangents[i]+=t.normalized()
for i,v in enumerate(verts):
    n=Vector(v[1]);t=tangents[i]-n*n.dot(tangents[i])
    if t.length_squared<1e-10:t=n.cross(Vector((0,0,1)))
    if t.length_squared<1e-10:t=n.cross(Vector((0,1,0)))
    v[2]=list(t.normalized())
(R/'mesh_source.json').write_text(json.dumps({'vertices':verts,'indices':indices,'triangle_materials':classes,'material_triangle_counts':counts,'height_cm':height,'front_game_direction':[0,0,1]}),encoding='utf8')
print(json.dumps({'vertices':len(verts),'triangles':len(indices)//3,'counts':counts}))
