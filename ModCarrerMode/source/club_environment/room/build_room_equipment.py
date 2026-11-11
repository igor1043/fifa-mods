"""Build optional gym equipment and a refreshed coach office, without changing a save.

Inputs are a Collada gym and the static NPZ/JSON interchange exported from Blender.
All output is staged beneath --output; installation is a separate operation.
"""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from collada_equipment import Collada
from room_prop_conversion import Palette,transform,without_coplanar_duplicates,merged_parts
from room_visual_r68 import read_mesh,replace_mesh,packed
from rx3 import Rx3,VERTEX
from trophy_room.assets import mesh_file,rx_texture

ROOT='data/sceneassets/server16_dressing_room_v3/'
GYM=ROOT+'rehab_equipment/'
OFFICE=ROOT+'office_refresh/'
SHARED=ROOT+'shared/'


def write_json(file,data):
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def native_box(lo,hi,pivot,destination,degrees=0,scale=1):
    points=np.array([[x,y+1000,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
    points,_=transform(points,np.tile([0,1,0],(8,1)),pivot,destination,degrees,scale)
    low,high=points.min(0),points.max(0);low[1]-=1000;high[1]-=1000
    return dict(lo=low.tolist(),hi=high.tolist())


def build(game,dae,interchange,output,office_manifest=None):
    game,output=Path(game),Path(output);interchange=Path(interchange)
    template=game/'ModCarrerMode/data/trophy_room/prop-template.rx3'
    texture_template=game/'ModCarrerMode/data/trophy_room/texture-template.rx3'
    for folder in (GYM,OFFICE,SHARED):(output/folder).mkdir(parents=True,exist_ok=True)
    palette=Palette();audit=[];meshes={}

    def imported(parts,name,destination,degrees=0,scale=1,linear=False):
        points=np.concatenate([p['p'] for p in parts]);lo,hi=points.min(0),points.max(0)
        pivot=(lo+hi)/2;pivot[1]=lo[1]
        parts=without_coplanar_duplicates(parts);count=0
        for part in parts:
            part['p'],part['n']=transform(part['p'],part['n'],pivot,destination,degrees,scale)
            material=part['material']
            part['uv']=np.tile(palette.uv(material['color'],linear),(len(part['p']),1))
            count+=len(part['idx'])//3
        points=np.concatenate([p['p'] for p in parts]);lo,hi=points.min(0),points.max(0)
        audit.append(dict(name=name,triangles=count,lo=lo.tolist(),hi=hi.tolist()))
        meshes[name]=parts
        return parts,lo,hi

    # Preserve authored dimensions, cm floor contact, proper normals and winding.
    gym=Collada(dae);gym_bindings=[];gym_obstacles=[];gym_parts=[]
    choices=[('ID7080','esteira',[-1018,1002.7,2681],90),
             ('ID6844','bicicleta',[-857,1002.7,2747],90),
             ('ID6802','espaldar',[-690,1002.7,2817],90),
             ('ID2693','banco_regulavel',[-560,1002.7,2655],0)]
    for node,name,position,yaw in choices:
        parts,lo,hi=imported(gym.extract(node),name,position,yaw)
        gym_parts.extend(parts)
        lo[1]-=1000;hi[1]-=1000;gym_obstacles.append(dict(name='Reabilitação / '+name,lo=lo.tolist(),hi=hi.tolist()))
    merged=merged_parts(gym_parts);model=GYM+'rehabilitation_r2.rx3';mesh_file(merged,template,output/model)
    for i in range(len(merged)):
        gym_bindings.append(dict(key='medical_rehab_'+str(i),model=model,texture=GYM+'palette.rx3',submesh=f'gallery_part_{i+1}'))

    # Keep the clinical room, all screens and treatments. Replace only rehab props.
    from room_medical_r77 import geometry
    from room_interior_r72 import write_groups
    groups,obstacles=geometry(rehab_furniture=False)
    own={k:v for k,v in groups.items() if k not in ('primary','secondary','floor','ceiling')}
    bindings=write_groups(game/SHARED/'locker_support_r68.rx3',own,output/GYM/'medical_room_r77.rx3')
    write_json(output/GYM/'medical_room.json',dict(revision=1,bindings=bindings,obstacles=obstacles))
    write_json(output/GYM/'equipment.json',dict(schema=1,units='cm',bindings=gym_bindings,obstacles=gym_obstacles,
        medical_spec=GYM+'medical_room.json',medical_model=GYM+'medical_room_r77.rx3',
        required=[GYM+'medical_room.json',GYM+'medical_room_r77.rx3']))

    office=copy.deepcopy(json.loads(Path(office_manifest or game/ROOT/'pes_office/office.json').read_text(encoding='utf8')))
    original_office=copy.deepcopy(office)
    if office.get('layout_revision',0)>=2:raise ValueError('Use the pre-refresh office manifest as build input')
    transforms={
        'desk_assembly':([460,1000,2100],[350,1000,2320],-90,1),
        'office_chair':([460,1000,2100],[350,1000,2320],-90,1),
        'tactical_board':([238,1000,2003],[660,1000,2490],0,1),
        'rolling_shelf':([207.2,1000,2120.2],[650,1000,1970],0,1),
        'sofa_set':([0,1000,2100],[-40,1000,2100],0,1),
        'coffee_table':([0,1000,2100],[-40,1000,2100],0,1),
        'table_vase':([0,1000,2100],[-40,1000,2100],0,1),
        'floor_plant':([561.6,1000,1876.8],[-220,1000,1740],0,1)}

    def furniture_model(original,target,conversion):
        rx=Rx3((game/original).read_bytes());pivot,destination,yaw,scale=conversion
        for slot in range(len(rx.get(VERTEX))):
            v,ids=read_mesh(rx,slot);normal=v['n'].astype(np.int64)
            n=np.stack([(normal>>s)&1023 for s in (0,10,20)],axis=1);n=np.where(n>=512,n-1024,n)/511
            v['p'],normals=transform(v['p'],n,pivot,destination,yaw,scale)
            v['n']=[packed(n) for n in normals]
            tangent=v['g'].astype(np.int64);g=np.stack([(tangent>>s)&1023 for s in (0,10,20)],axis=1);g=np.where(g>=512,g-1024,g)/511
            _,tangents=transform(np.zeros_like(g),g,[0,0,0],[0,0,0],yaw)
            v['g']=[packed(n) for n in tangents];replace_mesh(rx,slot,v,ids)
        (output/target).write_bytes(rx.build())

    original_bindings=copy.deepcopy(office['bindings'])
    for binding in office['bindings']:
        group=next((key for key in transforms if binding['key'].startswith('coach_pes_'+key+'_')),None)
        if group:
            target=OFFICE+Path(binding['model']).name
            furniture_model(binding['model'],target,transforms[group]);binding['model']=target
    for obstacle in office['obstacles']:
        name=obstacle['name'].split(' / ',1)[1]
        group='sofa_set' if name.startswith('seating') else name
        if group in transforms:obstacle.update(native_box(obstacle['lo'],obstacle['hi'],*transforms[group]))
    office['obstacles'].append(dict(name='Coach office / plant',lo=[-279,0,1692],hi=[-161,141,1788]))

    # Matching chairs face the trainer; leave a clear route between seats and door.
    chair_pivot=[536.3,1000,2100]
    for seat,x in enumerate((260,440),1):
        for source in original_bindings:
            if not source['key'].startswith('coach_pes_office_chair_'):continue
            b=copy.deepcopy(source);b['key']=f'coach_guest_{seat}_'+b['key'];target=OFFICE+f'guest_{seat}_'+Path(b['model']).name
            furniture_model(b['model'],target,(chair_pivot,[x,1000,2110],90,.86));b['model']=target;office['bindings'].append(b)
        old=next(p for p in original_office['obstacles'] if p['name'].endswith('/ office_chair'))
        office['obstacles'].append(dict(name=f'Coach office / guest chair {seat}',**native_box(old['lo'],old['hi'],chair_pivot,[x,1000,2110],90,.86)))

    rows={row['name']:row for row in json.loads((interchange/'office-meshes.json').read_bytes())}
    arrays=np.load(interchange/'office-meshes.npz',allow_pickle=False)
    selected=[('Cube.019','telefone',[260,1080.3,2340],180,.72),
              ('Cube.005','bandeja_documentos',[449,1080.3,2343],0,.50),
              ('Cube.013','pastas',[450,1087,2343],0,.34),
              ('Cube.018','documentos',[296,1080.3,2305],0,.55),
              ('Cylinder.006','caneca',[305,1080.3,2348],0,.55),
              ('Cube.006','radio',[650,1089.2,1970],0,.72)]
    for obj,name,position,yaw,scale in selected:
        row=rows[obj];parts=[]
        for b in row['parts']:
            parts.append(dict(**{key:arrays[b['prefix']+'_'+key].copy() for key in ('p','n','uv','idx')},material=b['material']))
        parts,lo,hi=imported(parts,name,position,yaw,scale,linear=True)
        merged=merged_parts(parts);model=OFFICE+name+'.rx3';mesh_file(merged,template,output/model)
        for i in range(len(merged)):
            office['bindings'].append(dict(key='coach_prop_'+name+'_'+str(i),model=model,texture=OFFICE+'palette.rx3',texname='equipment_cm',submesh=f'gallery_part_{i+1}',alpha=False))

    # Wall clock: preserve the source's actual face UVs; untextured rim uses palette.
    row=rows['Cylinder'];lo=np.array(row['lo']);hi=np.array(row['hi']);pivot=(lo+hi)/2;pivot[1]=lo[1]
    clock_parts=[];frame_parts=[]
    for b in row['parts']:
        part={key:arrays[b['prefix']+'_'+key].copy() for key in ('p','n','uv','idx')}
        part['p'],part['n']=transform(part['p'],part['n'],pivot,[150,1210,2586],180,.70)
        if np.ptp(part['uv'],axis=0).max()>.01:
            clock_parts.append(part);image=Image.open(b['material']['image']).convert('RGBA').resize((2048,2048),Image.Resampling.LANCZOS)
            rx_texture(image,texture_template,'equipment_cm',output/OFFICE/'clock-face.rx3')
        else:
            part['uv']=np.tile(palette.uv(b['material']['color'],True),(len(part['p']),1));frame_parts.append(part)
    for key,parts,texture in [('clock_face',clock_parts,'clock-face.rx3'),('clock_frame',frame_parts,'palette.rx3')]:
        model=OFFICE+key+'.rx3';merged=merged_parts(parts);mesh_file(merged,template,output/model)
        for i in range(len(merged)):office['bindings'].append(dict(key='coach_prop_'+key+'_'+str(i),model=model,texture=OFFICE+texture,texname='equipment_cm',submesh=f'gallery_part_{i+1}',alpha=False))
    # Batch static props with the same material. Keep the room comfortably below
    # the renderer's 256-component ceiling, including a full 38-player squad.
    def batch(bindings,name,texname):
        parts=[]
        for b in bindings:
            rx=Rx3((output/b['model']).read_bytes());v,idx=read_mesh(rx,0)
            bits=v['n'].astype(np.int64);n=np.stack([(bits>>s)&1023 for s in (0,10,20)],axis=1);n=np.where(n>=512,n-1024,n)/511
            parts.append(dict(p=v['p'],n=n,uv=v['uv'],idx=idx))
        merged=merged_parts(parts);model=OFFICE+name+'.rx3';mesh_file(merged,template,output/model)
        remove={b['key'] for b in bindings};office['bindings']=[b for b in office['bindings'] if b['key'] not in remove]
        for i in range(len(merged)):office['bindings'].append(dict(key='coach_'+name+'_'+str(i),model=model,texture=bindings[0]['texture'],texname=texname,submesh=f'gallery_part_{i+1}',alpha=False))
    batch([b for b in office['bindings'] if b.get('texname')=='equipment_cm' and b['texture'].endswith('palette.rx3')],'desktop_props_r2','equipment_cm')
    for suffix in ('atlas_0','8_14'):
        batch([b for b in office['bindings'] if b['key'].startswith('coach_guest_') and b['key'].endswith(suffix)],'guest_chairs_'+suffix,'office_cm')
    office['layout_revision']=2
    office['overview_pose']=[175,185,1710,260,125,2270,80]
    office['conversion'].append('Office refresh: static centimetre props, native 24-byte vertices; original shell, wall displays and exits retained.')
    write_json(output/ROOT/'pes_office/office.json',office)
    for folder in (GYM,OFFICE):rx_texture(palette.image(),texture_template,'equipment_cm',output/folder/'palette.rx3')
    write_json(output/'equipment-audit.json',dict(props=audit,office_bindings=len(office['bindings']),gym_bindings=len(gym_bindings)))
    return audit,meshes,office


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--game',type=Path,required=True);parser.add_argument('--gym',type=Path,required=True)
    parser.add_argument('--office-interchange',type=Path,required=True);parser.add_argument('--office-manifest',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    audit,_,office=build(args.game,args.gym,args.office_interchange,args.output,args.office_manifest)
    print(json.dumps(dict(props=len(audit),triangles=sum(p['triangles'] for p in audit),office_bindings=len(office['bindings'])),ensure_ascii=True))
