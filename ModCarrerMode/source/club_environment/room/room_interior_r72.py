"""Longer club room, fitted signs and detailed, naturally colored hydration props."""
from pathlib import Path
import copy, hashlib, io, json, math, struct
import numpy as np
from PIL import Image, ImageDraw
import portable_paths as portable
import room_interior_r71 as prior
from room_visual_r68 import VERT, box, join, packed, read_mesh, replace_mesh
from rx3 import Rx3, VERTEX, INDEX, FORMAT, NAME, MESH
from room_native_hanging_20261022 import texture_package

PREFIX=prior.PREFIX
EXTENSION=360.0
CUT=815.0


def shifted(z):return float(z)+(EXTENSION if float(z)>=CUT else 0)


def extend_vertices(vertices):
    v=vertices.copy();v['p'][:,2]+=np.where(v['p'][:,2]>=CUT,EXTENSION,0)
    return v


def wall_graphic_uv(vertices):
    """Fixed texel density: 2048 x 512 pixels per 240 x 60 cm wall area."""
    v=vertices.copy();packed_normals=v['n'].astype(np.int64)
    nx=packed_normals&1023;nz=(packed_normals>>20)&1023
    nx=np.where(nx>=512,nx-1024,nx)/511.;nz=np.where(nz>=512,nz-1024,nz)/511.
    v['uv'][:,0]=(v['p'][:,0]*nz-v['p'][:,2]*nx)/240.
    v['uv'][:,1]=-(v['p'][:,1]-1000)/60.
    return v


def layout(room,medical):
    room,medical=copy.deepcopy(room),copy.deepcopy(medical)
    for spec in (room,medical):
        for obstacle in spec['obstacles']:
            for key in ('lo','hi'):obstacle[key][2]=shifted(obstacle[key][2])
    room['camera_bounds']['front']=shifted(room['camera_bounds']['front'])
    room['hydration_origin'][2]=shifted(room['hydration_origin'][2])
    for key in ('lo','hi'):medical['room_bounds'][key][2]=shifted(medical['room_bounds'][key][2])
    for pose in medical['navigation']:
        pose[2]=shifted(pose[2]);pose[5]=shifted(pose[5])
    for scene in medical['scenes']:
        pose=scene['pose'];pose[2]=shifted(pose[2]);pose[5]=shifted(pose[5])
    return dict(revision=72,cut_cm=CUT,extension_cm=EXTENSION,room=room,medical=medical)


def lathe(center,profile,sides=32):
    center=np.array(center,dtype=float);rows=[];indices=[]
    for ring,(height,radius) in enumerate(profile):
        before=profile[max(0,ring-1)];after=profile[min(len(profile)-1,ring+1)]
        slope=(after[1]-before[1])/max(.0001,after[0]-before[0])
        for side in range(sides+1):
            angle=side*math.tau/sides;normal=np.array([math.cos(angle),-slope,math.sin(angle)]);normal/=np.linalg.norm(normal)
            pos=center+[radius*math.cos(angle),height,radius*math.sin(angle)]
            rows.append((pos,packed(normal),packed([-math.sin(angle),0,math.cos(angle)]),(side/sides,1-height/max(profile[-1][0],1))))
    for ring in range(len(profile)-1):
        for side in range(sides):
            a=ring*(sides+1)+side;b=a+sides+1;indices.extend([a,a+1,b+1,a,b+1,b])
    v=np.zeros(len(rows),dtype=VERT)
    for i,row in enumerate(rows):v[i]=row
    return v,np.array(indices,dtype='<u2')


def write_groups(template,groups,destination):
    rx=Rx3(Path(template).read_bytes());fmt=rx.get(FORMAT)[0];names=rx.get(NAME)[0];count=len(groups)
    rx.sections=[[0x22b2be36,struct.pack('<4I',count,0,0,0)+bytes(16*count),0]]+[[FORMAT,fmt,0] for _ in groups]+[[NAME,names,0]]+[[INDEX,bytes(16),0] for _ in groups]+[[VERTEX,bytes(16),0] for _ in groups]+[[MESH,struct.pack('<4I',4,0,0,0),0] for _ in groups]
    rx.set_names([(MESH,f'room_part_{i+1}.FxRenderableSimple') for i in range(count)])
    bindings=[]
    for i,(material,parts) in enumerate(groups.items()):
        v,idx=join(parts);replace_mesh(rx,i,v,idx);bindings.append(dict(material=material,submesh=f'room_part_{i+1}'))
    destination.write_bytes(rx.build());return bindings


def import_cooler(source,output,template):
    data=Path(source).read_bytes()
    if data[:4]!=b'glTF':raise ValueError('Expected GLB')
    length,kind=struct.unpack_from('<II',data,12);g=json.loads(data[20:20+length]);offset=20+length
    binary_size,binary_kind=struct.unpack_from('<II',data,offset);binary=data[offset+8:offset+8+binary_size]
    def accessor(index):
        a=g['accessors'][index];bv=g['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']];size=np.dtype(dtype).itemsize;cols={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']]
        return np.ndarray((a['count'],cols),dtype=dtype,buffer=binary,offset=bv.get('byteOffset',0)+a.get('byteOffset',0),strides=(bv.get('byteStride',size*cols),size)).copy()
    groups={};materials=[]
    # This CC0 file has translation-only mesh nodes, no skin or animation.
    for node in g['nodes']:
        if 'mesh' not in node:continue
        if any(k in node for k in ('matrix','rotation','scale')):raise ValueError('Unexpected cooler node transform')
        for p in g['meshes'][node['mesh']]['primitives']:
            a=p['attributes'];points=accessor(a['POSITION'])+node.get('translation',[0,0,0]);normals=accessor(a['NORMAL']);uv=accessor(a['TEXCOORD_0']);idx=accessor(p['indices']).reshape(-1).astype('<u2')
            # Its tap/niche protrude toward GLB +Z. Turn the complete object
            # toward the room (-Z), including normals, before metre->cm scale.
            points[:,[0,2]]*=-1;normals[:,[0,2]]*=-1
            points=points*125+[280,1000,911]
            v=np.zeros(len(points),dtype=VERT);v['p']=points;v['uv']=uv
            for j,n in enumerate(normals):v['n'][j]=packed(n);v['g'][j]=packed([1,0,0])
            mat=g['materials'][p['material']];key='cooler_body' if 'baseColorTexture' in mat['pbrMetallicRoughness'] else 'cooler_glass'
            groups.setdefault(key,[]).append((extend_vertices(v),idx))
            if key=='cooler_body':
                tex=g['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['source'];image=g['images'][tex];bv=g['bufferViews'][image['bufferView']];start=bv.get('byteOffset',0);im=Image.open(io.BytesIO(binary[start:start+bv['byteLength']])).convert('RGBA')
            else:
                color=mat['pbrMetallicRoughness']['baseColorFactor'];im=Image.new('RGBA',(8,8),tuple(round(c*255) for c in color))
            file=output/f'{key}_r72.rx3'
            if file.exists():file.unlink()
            texture_package(im,file,'cooler_cm')
    return write_groups(template,groups,output/'water_cooler_r72.rx3')


def stage(game,output,cooler_source):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True)
    prior.stage(game,output);base=game/PREFIX
    spec=json.loads((output/'interior_r71.json').read_text());rx=Rx3((output/'interior_r71.rx3').read_bytes());groups={}
    for i,binding in enumerate(spec['bindings']):
        v,idx=read_mesh(rx,i);tri=idx.reshape(-1,3);points=v['p'][tri]
        # Replace the first-version hydration objects while keeping the header,
        # graphics, door trim, exit and mural untouched.
        inside=prior.within(points,[300,999,850],[715,1241,941.1]);tri=tri[~inside]
        if len(tri):
            used,inv=np.unique(tri,return_inverse=True);groups[binding['material']]=[(v[used],inv.reshape(-1).astype('<u2'))]
        else:groups[binding['material']]=[]
    def add(key,part):groups.setdefault(key,[]).append(part)
    # Cabinet plinth, carcass, inset doors, counter and separate steel pulls.
    add('charcoal',box((325,1003,886),(620,1084,939)))
    add('seam',box((334,1000,891),(611,1006,937)))
    for x in [325,399,473,547]:
        add('cabinet_front',box((x+1,1009,880),(x+72,1082,886)))
        add('metal',box((x+15,1069,877.5),(x+58,1071.5,881)))
    add('counter',box((320,1084,876),(624,1090,942)))
    # Sealed dark refrigerator with rounded-looking trim, glass, real shelves,
    # warm/cool colored drinks and a separate interior panel/LED diffuser.
    for lo,hi in [((636,1000,885),(714,1090,941)),((636,1090,885),(641,1242,941)),((709,1090,885),(714,1242,941)),((641,1235,885),(709,1242,941)),((641,1090,937),(709,1235,941))]:add('charcoal',box(lo,hi))
    add('fridge_inner',prior.panel([675,1161,936.7],67,145,(0,0,-1)))
    add('glass',prior.panel([675,1161,883.7],67,141,(0,0,-1)))
    for x in [641,708]:add('metal',box((x,1090,883),(x+1.5,1235,885)))
    add('metal',box((710,1108,881),(712,1224,884)))
    add('light',box((643,1229,888),(707,1231,891)))
    for row,y in enumerate([1098,1140,1182]):
        add('metal',box((643,y,889),(707,y+1.5,934)))
        for j,x in enumerate([650,666,682,698]):
            key=['bottle','drink_amber','drink_red'][row]
            profile=[(0,0),(0,3.6),(.8,4),(4,4),(5,3.6),(6,4),(17,4),(18,3.8),(21,2.2),(25,1.8),(26,1.8),(26,0)]
            add(key,lathe([x,y+2,902],profile))
            add('cap_white',lathe([x,y+28,902],[(0,0),(0,2),(2,2),(2,0)],24))
            add('labels',prior.panel([x,y+16,897.8],7,10,(0,0,-1),(row/3,0,(row+1)/3,1)))
    add('charcoal',box((328,1180,911),(614,1184,939)))
    for x in [344,412]:
        for y in [1185,1192,1199]:
            add('towel',box((x,y,917),(x+56,y+6,937)))
            add('towel_edge',box((x+2,y+2,916.8),(x+54,y+3,917.2)))
    # Ribbed orange drink coolers: taper, shoulder, handle anchors, fitted lid,
    # a proper tap and contrasting white legs instead of plain club cylinders.
    for x in [355,412]:
        profile=[(0,0),(0,18),(1,20),(3,21)]+[(float(y),21 if y%4<2 else 20.5) for y in range(4,39)]+[(40,20),(41,18),(41,0)]
        add('orange_plastic',lathe([x,1091,909],profile,40))
        add('cap_white',lathe([x,1132,909],[(0,0),(0,22),(2,23),(4,22),(5,19),(5,0)],40))
        for side in [-1,1]:add('cap_white',box((x+side*22-1,1119,905),(x+side*22+1,1130,913)))
        add('cap_white',box((x-2,1097,884),(x+2,1108,889)))
        add('charcoal',box((x-1,1106,882),(x+1,1110,888)))
        add('cooler_label',prior.panel([x,1117,887.4],20,24,(0,0,-1)))
    # Squeezes with shaped shoulder/neck and molded lids, cups and a tray.
    for x in [485,503,521,539,557,575]:
        add('bottle_green',lathe([x,1091,909],[(0,0),(0,5),(2,5.5),(16,5.5),(19,4.5),(21,3),(22,3),(22,0)],28))
        add('orange_plastic',lathe([x,1113,909],[(0,0),(0,3.5),(1.5,3.5),(2,1.4),(5,1.4),(5,0)],28))
    add('metal',box((463,1090,882),(603,1092,931)))
    for x in [465,479,493]:add('cap_white',lathe([x,1093,892],[(0,0),(0,2),(14,3.4),(14,2.8),(1,1.6),(1,0)],24))
    # A slim recycling bin occupies the service block, not an existing aisle.
    add('bin',lathe([726,1000,920],[(0,0),(0,13),(3,14),(56,14),(58,12),(58,0)],32))
    add('metal',lathe([726,1057,920],[(0,0),(0,14),(2,14),(2,0)],32))
    # Normalize the header too: retain its atlas region without distorting type.
    if 'signs' in groups:
        parts=[]
        for v,idx in groups['signs']:
            mask=(v['p'][:,0]>300)&(v['p'][:,0]<620)&(v['p'][:,1]>1235)
            if mask.any():
                v=v.copy();v['p'][mask,1]=1247+(v['p'][mask,1]-1255)*(66/35)
            parts.append((v,idx))
        groups['signs']=parts
    groups={key:[(extend_vertices(v),idx) for v,idx in parts] for key,parts in groups.items() if parts}
    groups['graphic']=[(wall_graphic_uv(v),idx) for v,idx in groups['graphic']]
    bindings=write_groups(base/'locker_support_r68.rx3',groups,output/'interior_r72.rx3')
    (output/'interior_r73.rx3').write_bytes((output/'interior_r72.rx3').read_bytes())
    cooler_bindings=import_cooler(cooler_source,output,base/'locker_support_r68.rx3')
    for name in ['room_roles','scenery','medical_room','crest_surfaces','floor_shadows']:
        source=output/f'{name}_r71.rx3'
        if not source.is_file():source=base/f'{name}_r62.rx3' if name=='crest_surfaces' else base/f'{name}_r56.rx3'
        rx=Rx3(source.read_bytes())
        for slot in range(len(rx.get(VERTEX))):
            if name=='medical_room' and slot in [6,7]:
                center=[-545 if slot==6 else 180,1261,942.2]
                v,idx=prior.panel(center,132,33,(0,0,-1))
            else:v,idx=read_mesh(rx,slot)
            v=extend_vertices(v)
            if (name in ['room_roles','medical_room'] and slot==3):v['uv']=v['p'][:,[0,2]]/60
            if name=='room_roles' and slot==2:v['uv']=v['p'][:,[0,2]]/60
            if name=='room_roles' and slot in [4,5]:
                frames=slot==4;margin=30 if frames else 28
                low,high=(1318.4,1320) if frames else (1318,1318.3)
                v,idx=join([(v,idx)]+[box((x-margin,low,z-margin),(x+margin,high,z+margin)) for x in [-450,30,450] for z in [930,1170]])
            replace_mesh(rx,slot,v,idx)
        (output/f'{name}_r72.rx3').write_bytes(rx.build())
    for source,dest in [('ceiling_r71.rx3','ceiling_r72.rx3'),('scenery_textures_0_r71.rx3','scenery_textures_0_r72.rx3'),('scenery_textures_1_r71.rx3','scenery_textures_1_r72.rx3')]:
        (output/dest).write_bytes((output/source).read_bytes())
    room=json.loads((game/'ModCarrerMode/data/club_environment/room/runtime/room_roles_r62.json').read_text(encoding='utf8'))
    medical=json.loads((game/'ModCarrerMode/data/club_environment/room/runtime/medical_room_r57.json').read_text(encoding='utf8'))
    (output/'room_layout_r72.json').write_text(json.dumps(layout(room,medical),ensure_ascii=False,indent=2),encoding='utf8')
    extra=[dict(name='Hidratação / bancada r72',lo=[320,0,876],hi=[624,90,942]),dict(name='Hidratação / refrigerador r72',lo=[636,0,883],hi=[714,242,941]),dict(name='Hidratação / bebedouro r72',lo=[254,0,883],hi=[313,140,940]),dict(name='Hidratação / lixeira r72',lo=[712,0,906],hi=[740,59,934])]
    for o in extra:
        for key in ['lo','hi']:o[key][2]=shifted(o[key][2])
    result=dict(revision=72,bindings=bindings,cooler_bindings=cooler_bindings,obstacles=extra,extension_cm=EXTENSION)
    (output/'interior_r72.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');return result


def prepare(context,read_asset,add,identity):
    live=portable.GAME/PREFIX;spec=json.loads((live/'interior_r72.json').read_text(encoding='utf8'));club=context['club'];colors=context['colors'];primary,secondary=prior.palette(colors)
    model='interior_r73.rx3' if (live/'interior_r73.rx3').is_file() else 'interior_r72.rx3'
    architectural_finish=(live/'interior_r74.rx3').is_file() and (live/'interior_r74.json').is_file()
    if architectural_finish:
        spec=json.loads((live/'interior_r74.json').read_text(encoding='utf8'));model='interior_r74.rx3'
    secondary_wall=(live/'interior_r75.rx3').is_file() and (live/'interior_r75.json').is_file()
    if secondary_wall:
        spec=json.loads((live/'interior_r75.json').read_text(encoding='utf8'));model='interior_r75.rx3';architectural_finish=True
    if (live/'interior_r76.rx3').is_file() and (live/'interior_r76.json').is_file():
        spec=json.loads((live/'interior_r76.json').read_text(encoding='utf8'));model='interior_r76.rx3'
    if (live/'interior_r77.rx3').is_file() and (live/'interior_r77.json').is_file():
        spec=json.loads((live/'interior_r77.json').read_text(encoding='utf8'));model='interior_r77.rx3'
    hydration=(live/'interior_r78.rx3').is_file() and (live/'interior_r78.json').is_file()
    if hydration:
        spec=json.loads((live/'interior_r78.json').read_text(encoding='utf8'));model='interior_r78.rx3'
    try:crest=Image.open(io.BytesIO(read_asset(f'data/ui/imgassets/crest/light/l{club}.dds'))).convert('RGBA')
    except (FileNotFoundError,OSError,ValueError):crest=None
    atlas=Image.new('RGBA',(2048,2048))
    for j,(title,symbol) in enumerate([('DEPARTAMENTO MÉDICO','medical'),('COMISSÃO TÉCNICA','coach'),('SAÍDA DO VESTIÁRIO','exit'),('HIDRATAÇÃO','water')]):atlas.paste(prior.club_sign(context,title,symbol,crest),(0,j*512))
    images=dict(signs=atlas,mural=prior.make_mural(context,crest))
    if architectural_finish:
        from room_interior_r74 import surface_images
        images.update(surface_images())
    else:images['graphic']=prior.graphic(colors)
    if secondary_wall:
        from room_secondary_wall_r75 import material_images
        images.update(material_images(context,portable.GAME))
    label=Image.new('RGBA',(1536,512),'white');d=ImageDraw.Draw(label)
    for j,(text,rgb) in enumerate([('ÁGUA',(25,108,165)),('ENERGIA',(224,136,30)),('REPOSIÇÃO',(182,33,58))]):
        x=j*512;d.rectangle((x,0,x+511,511),fill=rgb);d.text((x+256,256),text,font=prior.font(69),fill='white',anchor='mm')
    images['labels']=label
    images['cooler_label']=Image.new('RGBA',(512,512),(242,108,15,255));d=ImageDraw.Draw(images['cooler_label']);d.text((256,180),'H₂O',font=prior.font(155),fill='white',anchor='mm');d.text((256,342),'HIDRATAÇÃO',font=prior.font(49),fill='white',anchor='mm')
    solids=dict(primary=primary,secondary=secondary,charcoal=(23,25,28),seam=(7,9,10),metal=(159,170,176),glass=(78,128,149),light=(240,252,255),towel=(237,236,228),towel_edge=(162,177,185),bottle=(140,201,221),drink_amber=(236,166,30),drink_red=(195,41,58),cap_white=(240,242,242),orange_plastic=(242,105,12),bottle_green=(25,119,78),cabinet_front=(35,40,44),counter=(56,64,67),fridge_inner=(91,112,122),bin=(31,42,52))
    for key,rgb in solids.items():images[key]=Image.new('RGBA',(8,8),rgb+(32 if key=='glass' else 255,))
    if hydration:
        from room_hydration_r78 import material_images,source
        images.update(material_images(context,crest,portable.GAME))
    for binding in spec['bindings']:
        key=binding['material']
        if hydration and key=='hydration_header' and source(portable.GAME,club):continue
        if key=='crest':texture=f'data/ui/imgassets/crest/light/l{club}.dds';texname=''
        else:
            im=images[key];tag=hashlib.sha256(im.tobytes()+str(im.size).encode()).hexdigest()[:16];filename=f'interior_{key}_{club}_{tag}_r72.rx3';path=live/filename
            if not path.exists():texture_package(im,path,'interior_cm')
            texture=PREFIX+filename;texname='interior_cm'
        add('interior_'+key,PREFIX+model,texture,texname,identity,key in ['glass','crest'],submesh=binding['submesh'])
    for binding in spec['cooler_bindings']:
        key=binding['material'];add(key,PREFIX+spec.get('cooler_model','water_cooler_r72.rx3'),PREFIX+key+'_r72.rx3','cooler_cm',identity,key.endswith('glass'),submesh=binding['submesh'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--game',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--cooler',required=True,type=Path);a=p.parse_args();print(json.dumps(stage(a.game,a.output,a.cooler)))
