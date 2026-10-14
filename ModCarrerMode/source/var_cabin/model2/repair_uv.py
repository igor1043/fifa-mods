from pathlib import Path
import bpy,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent
OLD=R.parent/'35_CABINE_VAR_20261013'
bpy.ops.wm.open_mainfile(filepath=str(R/'source.blend'))
new=[o for o in bpy.context.scene.objects if o.type=='MESH']
with bpy.data.libraries.load(str(OLD/'source.blend'),link=False) as (a,b):b.objects=a.objects
old=[o for o in b.objects if o and o.type=='MESH']
for o in old:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
points=[];triangles=[];uvs=[]
for o in old:
    m=o.data;m.calc_loop_triangles();offset=len(points)
    points.extend(o.matrix_world@v.co for v in m.vertices)
    for t in m.loop_triangles:
        triangles.append(tuple(offset+i for i in t.vertices))
        uvs.append([m.uv_layers.active.data[l].uv.copy() for l in t.loops])
tree=BVHTree.FromPolygons(points,triangles,all_triangles=True)
newpoints=[o.matrix_world@v.co for o in new for v in o.data.vertices]
oldlo=Vector(tuple(min(p[a] for p in points) for a in range(3)));oldhi=Vector(tuple(max(p[a] for p in points) for a in range(3)))
newlo=Vector(tuple(min(p[a] for p in newpoints) for a in range(3)));newhi=Vector(tuple(max(p[a] for p in newpoints) for a in range(3)))
def bary(p,a,b,c):
    v0=b-a;v1=c-a;v2=p-a;d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1);d20=v2.dot(v0);d21=v2.dot(v1)
    den=d00*d11-d01*d01
    if abs(den)<1e-16:return (1,0,0)
    v=(d11*d20-d01*d21)/den;w=(d00*d21-d01*d20)/den;return (1-v-w,v,w)
distances=[]
for o in new:
    m=o.data
    for p in m.polygons:
        if p.material_index!=0:continue
        transformed=[]
        for li in p.loop_indices:
            co=o.matrix_world@m.vertices[m.loops[li].vertex_index].co
            co=Vector(tuple(oldlo[a]+(co[a]-newlo[a])*(oldhi[a]-oldlo[a])/(newhi[a]-newlo[a]) for a in range(3)))
            transformed.append((li,co))
        center=sum((co for li,co in transformed),Vector())/len(transformed)
        closest,normal,t,distance=tree.find_nearest(center)
        assert t is not None
        # Keep all corners on one source UV chart. Independent nearest-corner
        # lookup bridges unrelated UV islands and creates coloured seam streaks.
        for li,co in transformed:
            weights=bary(co,*[points[i] for i in triangles[t]])
            m.uv_layers.active.data[li].uv=sum((uvs[t][i]*weights[i] for i in range(3)),Vector((0,0)))
            distances.append(distance)
    m.update()
for o in old:bpy.data.objects.remove(o,do_unlink=True)
distances.sort();report={'body_loops_transferred':len(distances),'nearest_distance_m':{'median':distances[len(distances)//2],'p95':distances[int(len(distances)*.95)],'maximum':max(distances)},'source':'old FBX world-space barycentric UV transfer; mirror material kept separate'}
(R/'uv_repair.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'repaired.blend'))
