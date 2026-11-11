"""Export the approved physical board, without its dynamic image or studio."""
import argparse,json,sys
from pathlib import Path
import bpy
import numpy as np

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False,use_scripts=False)
args.output.mkdir(parents=True,exist_ok=True)
depsgraph=bpy.context.evaluated_depsgraph_get();axis=np.array([[1,0,0],[0,0,1],[0,-1,0]])
arrays={};rows=[]
groups={'Satin aluminum':'metal','Matte back and corner details':'dark',
        'White board surface':'white','Rubber wheels':'rubber'}
for obj in bpy.data.objects:
    if obj.type!='MESH' or obj.name.startswith(('Studio ground','role_')):continue
    evaluated=obj.evaluated_get(depsgraph);mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
    matrix=np.asarray(obj.matrix_world);normal_matrix=np.linalg.inv(matrix[:3,:3])
    for material_index in sorted({tri.material_index for tri in mesh.loop_triangles}):
        material=mesh.materials[material_index]
        shader=material.node_tree.nodes.get('Principled BSDF')
        color=list(shader.inputs['Base Color'].default_value[:3])
        key=groups.get(material.name)
        if key is None:
            assert material.name.startswith('Marker cap '),material.name
            key='markers'
        points=[];normals=[]
        for tri in mesh.loop_triangles:
            if tri.material_index!=material_index:continue
            for vertex,loop in zip(tri.vertices,tri.loops):
                points.append(mesh.vertices[vertex].co)
                normals.append(mesh.corner_normals[loop].vector)
        p=(np.asarray(points)@matrix[:3,:3].T+matrix[:3,3])@axis.T*100+[0,1000,-513]
        n=np.asarray(normals)@normal_matrix@axis.T
        n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-10)
        prefix='part_'+str(len(rows));arrays[prefix+'_p']=p.astype('<f4');arrays[prefix+'_n']=n.astype('<f4')
        rows.append(dict(prefix=prefix,name=obj.name,group=key,color_linear=color,triangles=len(p)//3))
    evaluated.to_mesh_clear()
np.savez_compressed(args.output/'board-frame.npz',**arrays)
(args.output/'board-frame.json').write_text(json.dumps(dict(schema=1,units='cm',
    dynamic_image=dict(lo=[-117.5,1094,-512.55],hi=[117.5,1242,-512.55]),parts=rows),indent=2),encoding='utf8')
print('EXPORTED',len(rows),'parts',sum(r['triangles'] for r in rows),'triangles')
