"""Build the approved clinic and hydration replacements into a separate output tree."""
from pathlib import Path
import argparse,hashlib,json,math,shutil
from collections import defaultdict
import numpy as np
from PIL import Image
from rx3 import Rx3,VERTEX,read_model
from room_visual_r68 import read_mesh,packed
from room_interior_r72 import write_groups
from room_prop_conversion import transform,merged_parts,Palette
from trophy_room.assets import mesh_file,rx_texture
import medical_department_geometry as geo

PREFIX='data/sceneassets/server16_dressing_room_v3/medical_department/'
COLORS=dict(white='#f0f1ee',floor='#cdd0d0',ceiling='#f0f1ef',trim='#b7bfc1',metal='#a8b2b6',
 padding='#354856',frame='#252c31',rubber='#262a2d',belt='#212528',rug='#858c90',wood='#b49c7c',
 worktop='#e4e7e6',cabinet='#e7eae8',sink='#8f9da3',linen='#f4f2eb',light='#fffef7',screen='#234954',safety='#ae2528')


def normals(v):
 raw=v['n'].astype(np.int64);n=np.column_stack([(raw>>(10*i))&1023 for i in range(3)])
 return np.where(n>=512,n-1024,n)/511.


def oriented(shape):
 v,indices=shape;tri=indices.reshape(-1,3).copy();p=v['p'][tri];n=normals(v)[tri].mean(1)
 flip=(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])*n).sum(1)<0;tri[flip]=tri[flip][:,[0,2,1]]
 return v,tri.reshape(-1).astype('<u2')


def split(groups):
 result={};materials={}
 for material,parts in groups.items():
  batch=[];count=0;index=0
  for part in parts:
   if batch and count+len(part[0])>55000:
    key=f'{material}_{index}';result[key]=batch;materials[key]=material;batch=[];count=0;index+=1
   batch.append(oriented(part));count+=len(part[0])
  if batch:key=f'{material}_{index}';result[key]=batch;materials[key]=material
 return result,materials


def build(game,interchange,output,poster_dir):
 game,interchange,output,poster_dir=map(Path,(game,interchange,output,poster_dir))
 metadata=json.loads((interchange/'assets.json').read_text(encoding='utf8'));by_name={r['name']:r for r in metadata}
 digest=hashlib.sha256()
 for p in [Path(__file__),Path(geo.__file__),interchange/'assets.json',*sorted(interchange.glob('*.npz')),*sorted(poster_dir.glob('*.png'))]:digest.update(p.read_bytes())
 root=PREFIX+'r1_'+digest.hexdigest()[:14]+'/';folder=output/root;folder.mkdir(parents=True,exist_ok=True)
 template=game/'data/sceneassets/server16_dressing_room_v3/shared/locker_support_r68.rx3'
 texture_template=game/'ModCarrerMode/data/trophy_room/texture-template.rx3'
 prop_template=game/'ModCarrerMode/data/trophy_room/prop-template.rx3';audit=[];required=set();model_records=[]
 def texture(image,name):
  relative=root+name+'.rx3';rx_texture(image,texture_template,'medical_cm',output/relative);required.add(relative)
  image.save(folder/(name+'.png'));return relative
 palette=Palette();palette_uv={key:palette.uv(np.array(Image.new('RGB',(1,1),value).getpixel((0,0)))/255.) for key,value in COLORS.items()}
 materials={'clinical_flat':texture(palette.image(),'clinical_palette')}
 def geometry(name,scene):
  batched=defaultdict(list)
  for key,parts in scene.groups.items():
   for v,idx in parts:
    if key in palette_uv:
     v=v.copy();v['uv']=palette_uv[key];batched['clinical_flat'].append((v,idx))
    else:batched[key].append((v,idx))
  groups,lookup=split(batched);relative=root+name+'.rx3';bindings=write_groups(template,groups,output/relative);required.add(relative)
  for binding in bindings:binding['batch']=binding['material'];binding['material']=lookup[binding['material']]
  model_records.append(dict(model=relative,bindings=bindings))
  audit.append(dict(name=name,vertices=sum(len(v) for parts in groups.values() for v,i in parts),triangles=sum(len(i)//3 for parts in groups.values() for v,i in parts),materials=len(bindings)))
  return relative,bindings
 clinic=geo.clinical();rehab=geo.rehabilitation()
 for key,parts in rehab.groups.items():clinic.groups[key].extend(parts)
 clinic.obstacles.extend(rehab.obstacles)
 model,bindings=geometry('medical_room_r77',clinic)
 cardio=[]
 for name,scene,positions in [('treadmill',geo.treadmill(),[[-740,1000.5,2490],[-520,1000.5,2490]]),('bicycle',geo.bicycle(),[[-740,1000.5,2110],[-520,1000.5,2110]])]:
  native,parts=geometry(name,scene);cardio.append(dict(name=name,model=native,bindings=parts,positions=positions))
  for x,y,z in positions:
   lo,hi=([-62,y,z-123],[62,y+133,z+123]) if name=='treadmill' else ([-40,y,z-57],[40,y+116,z+57])
   clinic.obstacles.append(dict(name='Medical department / '+name,lo=[x+lo[0],0,lo[2]],hi=[x+hi[0],hi[1]-1000,hi[2]]))
 imported=[];texture_cache={}
 def imported_mesh(name,position,height=None,degrees=0,scale=100.,hydration=False):
  spec=by_name[name];data=np.load(interchange/(name+'.npz'),allow_pickle=False);lo=np.array(spec['lo']);hi=np.array(spec['hi']);pivot=(lo+hi)/2;pivot[1]=lo[1]
  factor=height/(hi[1]-lo[1]) if height else scale
  for row in spec['parts']:
   i=row['index'];p,n=transform(data[f'{i}_p'],data[f'{i}_n'],pivot,[0,0,0] if hydration else position,degrees,factor)
   uv=data[f'{i}_uv'].copy();uv[:,1]=1-uv[:,1]
   if row['image']:
    path=Path(row['image']);key=str(path)
    if key not in texture_cache:
     with Image.open(path) as im:image=im.convert('RGBA');image.thumbnail((2048,2048),Image.Resampling.LANCZOS)
     texture_cache[key]=texture(image,'import_'+hashlib.sha256(path.read_bytes()).hexdigest()[:14])
    tex=texture_cache[key]
   else:
    rgba=np.clip(np.array(row['color']),0,1);rgb=np.where(rgba[:3]<=.0031308,rgba[:3]*12.92,1.055*rgba[:3]**(1/2.4)-.055)
    tex=texture(Image.new('RGBA',(8,8),tuple(np.rint(rgb*255).astype(int))+(255,)),name+'_color_'+str(i))
   meshes=merged_parts([dict(p=p,n=n,uv=uv,idx=data[f'{i}_idx'])]);relative=root+name+'_'+str(i)+'.rx3';mesh_file(meshes,prop_template,output/relative);required.add(relative)
   for sub in range(len(meshes)):imported.append(dict(key='medical_import_'+name+'_'+str(i)+'_'+str(sub),model=relative,texture=tex,texname='medical_cm',submesh=f'gallery_part_{sub+1}',alpha=False,hydration=hydration))
  audit.append(dict(name=name,source=Path(spec['source']).name,triangles=spec['triangles'],height_cm=float((hi[1]-lo[1])*factor),hydration=hydration))
  if not hydration:
   corners=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]);points,_=transform(corners,np.tile([0,1,0],(8,1)),pivot,position,degrees,factor)
   low,high=points.min(0),points.max(0);low[1]-=1000;high[1]-=1000;clinic.obstacles.append(dict(name='Medical department / '+name,lo=low.tolist(),hi=high.tolist()))
 imported_mesh('MSH_Bench_01',[-1065,1000.5,2780])
 imported_mesh('MSH_Rack_01',[-470,1000.5,2790],degrees=90)
 imported_mesh('MSH_AbWheel',[-1170,1001,2760])
 for name,position in [('MSH_DumbBell_01',[-490,1022,2765]),('MSH_DumbBell_02',[-490,1055,2810]),('MSH_KettleBell_01',[-560,1001,2815]),('MSH_Plate_01',[-440,1003,2800])]:imported_mesh(name,position)
 imported_mesh('bottle',[0,0,0],height=26.,degrees=180,hydration=True)
 imported_mesh('cooler',[0,0,0],height=46.,degrees=180,hydration=True)
 # All small gym props share their original atlas. Batch those world-space
 # meshes without changing any position, UV, normal or source texture.
 grouped=defaultdict(list)
 for binding in imported:
  if not binding['hydration']:grouped[(binding['texture'],binding['texname'],binding['alpha'])].append(binding)
 imported=[b for b in imported if b['hydration']]
 for i,((tex,texname,alpha),items) in enumerate(grouped.items()):
  parts=[]
  for item in items:
   piece=read_model(Rx3((output/item['model']).read_bytes()))[0][int(item['submesh'].rsplit('_',1)[1])-1]
   parts.append(dict(p=np.array(piece['positions']).reshape(-1,3),n=np.array(piece['normals']).reshape(-1,3),uv=np.array(piece['uvs']).reshape(-1,2),idx=np.array(piece['indices'],dtype='<u4')))
  meshes=merged_parts(parts);relative=root+'fitness_batch_'+str(i)+'.rx3';mesh_file(meshes,prop_template,output/relative);required.add(relative)
  for sub in range(len(meshes)):imported.append(dict(key=f'medical_fitness_{i}_{sub}',model=relative,texture=tex,texname=texname,submesh=f'gallery_part_{sub+1}',alpha=alpha,hydration=False))
 # Reuse the already converted desk, notebook, chairs, telephone and cup.
 office=json.loads((game/'data/sceneassets/server16_dressing_room_v3/pes_office/office.json').read_text(encoding='utf8'));office_bindings=[];copied_textures={}
 for b in office['bindings']:
  if not any(key in b['key'] for key in ('desk_assembly','office_chair','desktop_props','guest_chairs')):continue
  rx=Rx3((game/b['model']).read_bytes());slot=int(b['submesh'].rsplit('_',1)[1])-1;v,idx=read_mesh(rx,slot);tri=idx.reshape(-1,3)
  if 'desktop_props' in b['key']:
   p=v['p'][tri];keep=((p>=[115,1079,2180])&(p<=[405,1150,2310])).all((1,2));tri=tri[keep]
  if not len(tri):continue
  used,inverse=np.unique(tri,return_inverse=True);v=v[used].copy();v['p'] += [-1470,0,-520]
  model=root+b['key']+'.rx3';parts=merged_parts([dict(p=v['p'],n=normals(v),uv=v['uv'],idx=inverse.reshape(-1).astype('<u4'))]);mesh_file(parts,prop_template,output/model);required.add(model)
  if b['texture'] not in copied_textures:
   tex=root+'office_'+hashlib.sha256(b['texture'].encode()).hexdigest()[:14]+'.rx3';shutil.copy2(game/b['texture'],output/tex);copied_textures[b['texture']]=tex;required.add(tex)
  for i in range(len(parts)):office_bindings.append(dict(key='medical_'+b['key']+'_'+str(i),model=model,texture=copied_textures[b['texture']],texname=b.get('texname','office_cm'),submesh=f'gallery_part_{i+1}',alpha=b['alpha']))
 grouped=defaultdict(list)
 for binding in office_bindings:
  key=(hashlib.sha256((output/binding['texture']).read_bytes()).hexdigest(),binding['texname'],binding['alpha']);grouped[key].append(binding)
 office_bindings=[]
 for i,items in enumerate(grouped.values()):
  if len(items)==1:office_bindings.extend(items);continue
  parts=[]
  for item in items:
   piece=read_model(Rx3((output/item['model']).read_bytes()))[0][int(item['submesh'].rsplit('_',1)[1])-1]
   parts.append(dict(p=np.array(piece['positions']).reshape(-1,3),n=np.array(piece['normals']).reshape(-1,3),uv=np.array(piece['uvs']).reshape(-1,2),idx=np.array(piece['indices'],dtype='<u4')))
  meshes=merged_parts(parts);relative=root+'office_batch_'+str(i)+'.rx3';mesh_file(meshes,prop_template,output/relative);required.add(relative)
  for sub in range(len(meshes)):office_bindings.append(dict(items[0],key=f'medical_office_{i}_{sub}',model=relative,submesh=f'gallery_part_{sub+1}'))
 static_posters={}
 for key in ('knee','spine'):
  with Image.open(poster_dir/(key+'.png')) as im:image=im.convert('RGBA')
  static_posters[key]=texture(image,key+'_poster')
 spec=dict(schema=1,revision=1,root=root,model=model_records[0]['model'],bindings=bindings,materials=materials,posters=static_posters,cardio=cardio,imported=imported,office=office_bindings,
           obstacles=clinic.obstacles,bounds=dict(lo=[geo.LEFT,0,geo.FRONT],hi=[geo.RIGHT,geo.TOP-1000,geo.BACK]),scenes=geo.SCENES,
           hydration=dict(bottle_positions=[[x,1095,1505] for x in (350,366,382,398,414,430)],cooler_positions=[[x,1095,1505] for x in (573,627)]),required=sorted(required),audit=audit,model_records=model_records)
 # Publish manifest only after every generated model and material is complete.
 parent=output/PREFIX;parent.mkdir(parents=True,exist_ok=True);(parent/'clinic.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
 (folder/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
 return spec


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--game',type=Path,required=True);parser.add_argument('--interchange',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--posters',type=Path,required=True);args=parser.parse_args()
 spec=build(args.game,args.interchange,args.output,args.posters);print(json.dumps(dict(root=spec['root'],models=len(spec['model_records']),imported=len(spec['imported']),office=len(spec['office']),obstacles=len(spec['obstacles']))))
