import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
import argparse,sys
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);base=args.source;r=args.output;r.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(next((base/'source').glob('*.blend'))),load_ui=False,use_scripts=False)
normalize=lambda x:''.join(c for c in x.lower() if c.isalnum()).replace('jpg','jpeg')
files={normalize(f.name):f for f in (base/'textures').iterdir() if f.is_file()}
for image in bpy.data.images:
 key=normalize(Path(image.filepath.replace('\\','/')).name)
 if key in files:image.filepath=str(files[key]);image.reload()
rows=[];arrays={};axis=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
for o in bpy.data.objects:
 if o.type!='MESH' or not o.data.polygons:continue
 mesh=o.data;mesh.calc_loop_triangles();matrix=np.asarray(o.matrix_world);nmat=np.linalg.inv(matrix[:3,:3]);parts=[]
 for slot in sorted({t.material_index for t in mesh.loop_triangles}):
  triangles=[t for t in mesh.loop_triangles if t.material_index==slot];p=[];n=[];uv=[]
  for t in triangles:
   for vertex,loop in zip(t.vertices,t.loops):
    p.append(mesh.vertices[vertex].co);n.append(mesh.vertices[vertex].normal if mesh.polygons[t.polygon_index].use_smooth else t.normal);uv.append(mesh.uv_layers.active.data[loop].uv if mesh.uv_layers.active else (0,0))
  p=(np.asarray(p)@matrix[:3,:3].T+matrix[:3,3])@axis.T*100;n=np.asarray(n)@nmat@axis.T;n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-9);uv=np.asarray(uv);uv[:,1]=1-uv[:,1]
  material=o.data.materials[slot] if slot<len(o.data.materials) else None;color=list(material.diffuse_color) if material else [.5,.5,.5,1];image=None
  if material and material.use_nodes:
   imgs=[node.image for node in material.node_tree.nodes if node.type=='TEX_IMAGE' and node.image and Path(node.image.filepath).is_file()]
   if imgs:image=Path(imgs[0].filepath)
  # The supplied pack's legacy materials share one palette atlas. Resolve
  # only packaged images; never follow missing author-computer paths.
  if image is None and material and mesh.uv_layers.active:image=files.get(normalize("60's_office_textures_1-01.png"))
  index=len(rows);part=len(parts);prefix=f'o{index}_p{part}'
  arrays[prefix+'_p']=p;arrays[prefix+'_n']=n;arrays[prefix+'_uv']=uv;arrays[prefix+'_idx']=np.arange(len(p),dtype=np.uint32)
  parts.append(dict(prefix=prefix,material=dict(id=material.name if material else 'none',color=color,image=str(image) if image else None)))
 allp=np.concatenate([arrays[m['prefix']+'_p'] for m in parts]);rows.append(dict(name=o.name,parts=parts,lo=allp.min(0).tolist(),hi=allp.max(0).tolist(),triangles=sum(len(arrays[m['prefix']+'_idx'])//3 for m in parts)))
np.savez_compressed(r/'office-meshes.npz',**arrays);(r/'office-meshes.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print('EXPORTED',len(rows))
