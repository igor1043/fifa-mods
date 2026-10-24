"""Build the custom room mesh; never edits FIFA assets or a career save.

The studio scene is an optional development input, not a runtime dependency.
Output is staged in --output and must be installed with its matching atlases.
"""
import argparse,collections,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
import portable_paths as portable
import room_scene_native_assets_20261022 as scene
import room_precise_mesh_r49 as mesh
from room_native_hanging_20261022 import texture_package
from room_geometry_clip_r54 import open_medical_annex
from room_geometry_rules_r56 import old_medical

def omit_part(p):
    name=p['name'];points=p['v']['p'];extent=np.ptp(points,axis=0)
    if name.startswith('Salas / portas abertas'):
        # Both old upper labels and side plaques are superseded by the single
        # dynamic medical/coach sign. Retain the door, jamb and handle.
        if any(word in name for word in ('placa','bras','superior')):return True
        if name=='Salas / portas abertas' and p['tex']>=0:return True
    if name.startswith('Armário'):
        if '/ costura do assento' in name:return True
        # Original grey cylindrical rail, not the cushion or its frame.
        if len(points)==120 and extent[1]<3 and min(extent[0],extent[2])<3 and max(extent[0],extent[2])>60 and 210<points[:,1].min()<216:return True
    return False

def material_tile(p,decode):
    # Solid materials must not share a small atlas cell with club-red parts.
    # They are assigned a dedicated solid texture in the component manifest.
    return decode(p['tex'])

def build(source,output,seed):
    output.mkdir(parents=True,exist_ok=True)
    scene.SOURCE=source;scene.LIVE=output;mesh.LIVE=output
    rows,decode=scene.scene_parts();keys={};custom=[];crests=[];removed=[]
    turn=np.diag([-1.,1.,-1.]);origin=np.array([-365.,0,629.]);target=np.array([440.,0,918.])
    for p in rows:
        if omit_part(p):removed.append(p['name']);continue
        if p['name'] in ('Sala / paredes externas','Sala / faixa do clube'):p['v'],p['idx']=open_medical_annex(p['v'],p['idx'])
        if p['name'].startswith('Hidrata'):p['v']['p']=(p['v']['p']-origin)@turn.T+target;p['v']['n']=p['v']['n']@turn.T
        if p['tex']==0:crests.append(p);continue
        native='/native/' in p['asset'] or p['asset'].startswith('data/') or 'kit-number/' in p['asset']
        plate=p['name'].startswith('Armário') and p['asset'].startswith('studio/room/') and p['tex']>=0 and p['tex']!=1
        if native or plate:continue
        key=(p['tex'],p['color'],p['blend'],p['alpha'])
        if key not in keys:keys[key]=len(keys)
        p['key']=keys[key]
        if not old_medical(p['name']):custom.append(p)
    pages=[Image.new('RGBA',(2048,2048),'white') for _ in range((len(keys)+63)//64)]
    for (tex,color,blend,alpha),i in keys.items():
        # 16px gutters reduce bleed for textured parts; solid panels below no
        # longer use this atlas at all, including distant mip levels.
        pix=np.array(decode(tex).resize((224,224),Image.Resampling.LANCZOS));pix[:,:,:3]=np.clip(pix[:,:,:3]*np.array(color),0,255).astype('uint8');pix[:,:,3]=(pix[:,:,3]*alpha).astype('uint8') if blend else 255
        pix=np.pad(pix,((16,16),(16,16),(0,0)),mode='edge');pages[i//64].paste(Image.fromarray(pix),((i%8)*256,(i%64//8)*256))
    for i,image in enumerate(pages):texture_package(image,output/f'scenery_textures_{i}_r62.rx3','room_cm')
    base=np.array([215/255,0,15/255]);neutral=collections.defaultdict(list);roles=collections.defaultdict(list)
    for p in custom:
        name=p['name'];v=p['v'];v['p'][:,1]+=1000
        if '/ cabide' in name:continue
        color=np.array(p['color']);factor=float(np.dot(color,base)/np.dot(base,base));primary=p['tex']==-1 and .25<factor<1.5 and np.max(np.abs(color-factor*base))<.003
        secondary=any(k in name.casefold() for k in ('friso','faixa secundária')) and p['tex']==-1
        if name=='Sala / piso' and p['tex']>=0:role=('floor',1.)
        elif name=='Sala / teto':
            from room_geometry_rules_r56 import ceiling_outside_clinic
            v,p['idx']=ceiling_outside_clinic(v,p['idx']);v['uv']=v['p'][:,[0,2]]/100;role=('ceiling',1.)
        elif p['asset'] in ('studio/live/central-tactics','studio/live/coach-match'):
            v['p']+=v['n']*.3;role=('board',1.)
        elif primary or secondary:role=('secondary' if secondary else 'primary',round(factor if primary else 1.,3))
        elif p['tex']==-1 and not p['blend']:
            role=('neutral',tuple(round(255*min(1,max(0,c))) for c in color))
        else:role=None
        if role is not None:
            if role[0] not in ('floor','ceiling','board'):v['uv'][:]=[.5,.5]
            roles[role].append((v,p['idx']));continue
        if name=='Sala / teto modular':
            from room_geometry_rules_r56 import ceiling_outside_clinic
            v,p['idx']=ceiling_outside_clinic(v,p['idx'])
        i=p['key'];uv=v['uv'];uv=np.where((uv>=0)&(uv<=1),uv,np.mod(uv,1));uv[:,0]=((i%8)*256+16+uv[:,0]*224)/2048;uv[:,1]=((i%64//8)*256+16+uv[:,1]*224)/2048;v['uv']=uv
        neutral[(i//64,p['blend'])].append((v,p['idx']))
    def batches(groups):
        result=[]
        for key,items in groups.items():
            vertices=[];indices=[];count=0
            for v,idx in items:
                if count+len(v)>58000:result.append((key,np.concatenate(vertices),np.concatenate(indices)));vertices=[];indices=[];count=0
                vertices.append(v);indices.append(idx+count);count+=len(v)
            if vertices:result.append((key,np.concatenate(vertices),np.concatenate(indices)))
        return result
    solid=batches(roles);textured=batches(neutral)
    work=output/'mesh-source';work.mkdir(exist_ok=True)
    mesh.precise_prop_file([(v,i) for _,v,i in solid],work/'room_roles_r62.rx3')
    mesh.precise_prop_file([(v,i) for _,v,i in textured],work/'scenery_r62.rx3')
    verts=[];indices=[];count=0
    for p in crests:
        v=p['v'];v['p'][:,1]+=1000;verts.append(v);indices.append(p['idx']+count);count+=len(v)
    mesh.precise_prop_file([(np.concatenate(verts),np.concatenate(indices))],work/'crest_surfaces_r62.rx3')
    spec=json.loads(seed.read_text(encoding='utf8'));spec['version']=62
    spec['neutral_bindings']=[list(k) for k,_,_ in textured]
    spec['roles']=[{'role':k[0],('rgb' if k[0]=='neutral' else 'shade'):k[1],'submesh':f'room_part_{i+1}'} for i,(k,_,_) in enumerate(solid)]
    # Geometry removals do not open any collision boundary. Preserve the
    # established camera obstacles and navigation anchors exactly.
    spec['removed_decorations']=removed
    (output/'room_roles_r62.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'textured_bindings':spec['neutral_bindings'],'roles':len(solid),'removed':len(removed),'pages':len(pages)}))
    return spec

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--seed',required=True,type=Path);args=parser.parse_args()
    build(args.source,args.output,args.seed)
