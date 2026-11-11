"""Rebuild the coach office while preserving the locker room and medical wing."""
from pathlib import Path
import copy,hashlib,json
import numpy as np
from PIL import Image
import portable_paths as portable
from rx3 import Rx3,VERTEX
from room_visual_r68 import VERT,box,join,packed,read_mesh,replace_mesh
from room_interior_r71 import PREFIX,panel,palette
from room_interior_r72 import write_groups,lathe
from room_secondary_wall_r75 import cushion,selected_palette
from room_native_hanging_20261022 import texture_package

LEFT=-324.;FRONT=1561.;BACK=2592.


def clip_office(vertices,indices,keep_door=False):
    """Subtract the office rectangle, clipping shared wall/floor triangles.

    A shared surface may span both rooms. Dropping its entire bounding box
    would also delete the medical wall; clipping preserves the outside half.
    """
    v=vertices;added=[];kept=[];count=len(v)
    def split(poly,axis,bound):
        inside=[];outside=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            av=float(a['p'][axis]-bound);bv=float(b['p'][axis]-bound)
            (inside if av>=0 else outside).append(a)
            if (av<0)!=(bv<0):
                t=av/(av-bv);p=a.copy();p['p']=a['p']+(b['p']-a['p'])*t;p['uv']=a['uv'].astype(float)+(b['uv'].astype(float)-a['uv'].astype(float))*t
                inside.append(p);outside.append(p.copy())
        return inside,outside
    def append(poly):
        nonlocal count
        if len(poly)<3:return
        for i in range(1,len(poly)-1):
            p=[poly[0],poly[i],poly[i+1]]
            if np.linalg.norm(np.cross(p[1]['p']-p[0]['p'],p[2]['p']-p[0]['p']))<.0001:continue
            added.extend(p);kept.extend([count,count+1,count+2]);count+=3
    for tri in indices.reshape(-1,3):
        p=v['p'][tri]
        doorway=keep_door and np.all((p[:,0]>=109)&(p[:,0]<=251)&(p[:,2]<=1662)&(p[:,1]<=1240))
        if doorway or p[:,0].max()<LEFT or p[:,2].max()<FRONT:kept.extend(tri);continue
        if p[:,0].min()>=LEFT and p[:,2].min()>=FRONT:continue
        ix,ox=split([v[i].copy() for i in tri],0,LEFT)
        append(ox)
        if ix:_,oz=split(ix,2,FRONT);append(oz)
    if not kept:return box((0,900,0),(.1,900.1,.1))
    vertices=np.concatenate([v,np.array(added,dtype=VERT)]) if added else v.copy()
    ids=np.array(kept,dtype='<u4');used,inverse=np.unique(ids,return_inverse=True)
    if len(used)>=65536:raise ValueError('Office clipping exceeds native index capacity')
    return vertices[used],inverse.reshape(-1).astype('<u2')


def horizontal(center,width,depth,cell):
    x,y,z=center;u0,v0,u1,v1=uv(cell);v=np.zeros(4,dtype=VERT)
    for i,(xx,zz,u,vv) in enumerate([(-1,-1,u0,v0),(-1,1,u0,v1),(1,1,u1,v1),(1,-1,u1,v0)]):v[i]=([x+xx*width/2,y,z+zz*depth/2],packed([0,1,0]),packed([1,0,0]),(u,vv))
    return v,np.array([0,1,2,0,2,3],dtype='<u2')


def region(cell,rect):
    x0,y0,x1,y1=rect
    return (cell%2*.5+x0/4096,cell//2*.25+y0/4096,cell%2*.5+x1/4096,cell//2*.25+y1/4096)


def uv(cell):
    return region(cell,(0,0,1024,512) if cell==6 else (0,0,2048,960) if cell==7 else (0,0,2048,1024))


def geometry(furniture=True):
    groups={k:[] for k in ('primary','secondary','dark','metal','light','floor','ceiling','panels')};obstacles=[]
    def add(key,shape):groups[key].append(shape)
    def solid(name,lo,hi):obstacles.append(dict(name='Sala do treinador R76 / '+name,lo=[lo[0],lo[1]-1000,lo[2]],hi=[hi[0],hi[1]-1000,hi[2]]))
    # Almost square 10.8 x 10.4 m interior; no window openings.
    for lo,hi in [((-325,1000,1560),(-320,1320,BACK)),((750,1000,1560),(756,1320,BACK)),((-325,1000,BACK),(756,1320,BACK+12))]:
        add('primary',box(lo,hi));solid('parede',lo,hi)
    v,idx=box((-325,999.8,1560),(756,1000.4,BACK));v['uv']=v['p'][:,[0,2]]/60;add('floor',(v,idx))
    v,idx=box((-325,1319.5,1560),(756,1326,BACK));v['uv']=v['p'][:,[0,2]]/60;add('ceiling',(v,idx))
    # Paint the inner faces of the existing front partition, preserving its door.
    for a,b in ((-324,115),(245,750)):add('primary',panel([(a+b)/2,1160,1558.5],b-a,320,(0,0,1)))
    add('primary',panel([180,1280,1558.5],130,80,(0,0,1)))
    add('secondary',panel([-319.6,1110,2080],1000,68,(1,0,0)))
    add('secondary',panel([749.6,1270,2080],1000,54,(-1,0,0)))
    add('secondary',panel([215,1045,BACK-.4],1070,75,(0,0,-1)))
    for x in (-320,749):add('dark',box((x,1000.4,1561),(x+1,1009,BACK)))
    # Simple flush ceiling luminaires, in the same 60 cm ceiling module.
    for x in (-150,210,570):
        for z in (1710,2070,2430):
            add('metal',box((x-30,1317.9,z-30),(x+30,1319.4,z+30)))
            add('light',box((x-28,1317.5,z-28),(x+28,1317.9,z+28)))
    if furniture:
        # Desk and integrated drawer pedestals, facing into the room.
        add('dark',box((40,1080,2070),(320,1086,2165)))
        add('secondary',box((42,1076,2072),(318,1080,2163)))
        for x in (60,255):
            add('primary',box((x,1003,2084),(x+45,1077,2155)))
            for y in (1024,1049):add('secondary',box((x+2,y,2083.5),(x+43,y+1.5,2084)))
            for y in (1015,1040,1065):add('metal',box((x+15,y,2082),(x+31,y+2,2084)))
        add('primary',box((103,1028,2085),(258,1076,2089)))
        solid('mesa',(40,1003,2070),(320,1086,2165))
        # Three actual chairs, with legs, arm rests, padded seats and backs.
        def chair(x,z,coach=False):
            add('dark',cushion((x-31,1043,z-30),(x+31,1050,z+30)))
            back=z+27 if coach else z-33
            add('dark',cushion((x-30,1058,back),(x+30,1147 if coach else 1128,back+7)))
            if coach:
                add('primary',box((x-28,1133,back-1),(x+28,1162,back+8)))
                add('metal',lathe([x,1004,z],[(0,0),(0,4),(37,4),(37,0)],20))
                for angle in np.linspace(0,2*np.pi,5,endpoint=False):
                    part,ids=box((-3,1003,0),(3,1007,33));p=part['p'];xx=p[:,0].copy();zz=p[:,2].copy();p[:,0]=x+xx*np.cos(angle)+zz*np.sin(angle);p[:,2]=z-xx*np.sin(angle)+zz*np.cos(angle);add('metal',(part,ids))
            else:
                for xx in (x-25,x+25):
                    for zz in (z-23,z+23):add('metal',box((xx-1.5,1001,zz-1.5),(xx+1.5,1044,zz+1.5)))
            for xx in (x-34,x+31):
                add('metal',box((xx,1040,z-16),(xx+3,1069,z+17)));add('dark',box((xx-2,1069,z-21),(xx+5,1073,z+22)))
            solid('cadeira',(x-36,1000,z-35),(x+36,1162 if coach else 1128,z+36))
        chair(180,2265,True);chair(95,1975);chair(265,1975)
        # Laptop, auxiliary tablet, tactical clipboard, papers, pens and squeeze.
        add('dark',box((111,1086,2098),(176,1088.5,2141)))
        add('dark',box((110,1088,2099),(177,1134,2103)))
        add('panels',panel([143.5,1111,2103.2],63,39,(0,0,1),uv(6)))
        add('dark',box((234,1086,2112),(282,1088,2146)))
        add('panels',horizontal([258,1088.2,2129],43,29,6))
        add('secondary',box((188,1086,2082),(229,1088,2136)))
        add('panels',horizontal([208,1088.2,2109],37,49,7))
        add('metal',box((202,1088.4,2083),(215,1089,2087)))
        for i in range(3):add('panels',horizontal([82+i*.7,1086.8+i*.3,2110+i*.8],25,37,7))
        for x in (241,246,251):add('metal',box((x,1086.2,2081),(x+1,1087,2101)))
        add('secondary',lathe([303,1086.2,2138],[(0,0),(0,4.5),(16,4.5),(20,2.5),(23,2.5),(23,0)],24))
        add('primary',lathe([303,1109.2,2138],[(0,0),(0,2.8),(2,2.8),(2,0)],24))
        # Low storage and archive trays along the left wall, not across the doorway.
        add('dark',box((-315,1000.5,1800),(-266,1087,2290)));solid('armário de apoio',(-315,1000.5,1800),(-266,1087,2290))
        for z in range(1803,2290,81):
            add('secondary',box((-265.8,1008,z),(-264,1080,min(z+76,2288))))
            add('metal',box((-263.5,1061,z+25),(-262,1064,z+53)))
        for z in (1850,1910,2150):
            add('primary',box((-307,1087,z),(-278,1112,z+43)));add('panels',horizontal([-291,1112.2,z+21],25,37,7))
    # Each physical panel maps to one sharp 2048 x 1024 atlas cell.
    boards=[(0,[120,1192,2587],380,190,(0,0,-1)),(1,[540,1180,2587],300,150,(0,0,-1)),
            (2,[-200,1180,2587],210,145,(0,0,-1)),(3,[746,1182,2260],300,150,(-1,0,0)),
            (4,[746,1180,1880],300,150,(-1,0,0)),(5,[-317,1190,2130],350,175,(1,0,0))]
    for cell,center,width,height,normal in boards:
        # Thin frames are actual backing planes, not a thick decorative border.
        n=np.array(normal);add('dark',panel((np.array(center)-n*.8).tolist(),width+6,height+6,normal))
        add('panels',panel(center,width,height,normal,uv(cell)))
    from room_coach_decor_r76 import decorate
    if furniture:decorate(add,solid,region)
    return groups,obstacles


def stage(game,output):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True);base=game/PREFIX
    groups,obstacles=geometry()
    for name in ('room_roles','scenery','crest_surfaces','floor_shadows'):
        rx=Rx3((base/(name+'_r75.rx3')).read_bytes())
        for slot in range(len(rx.get(VERTEX))):
            v,ids=read_mesh(rx,slot);v,ids=clip_office(v,ids,keep_door=name=='room_roles')
            if name=='room_roles' and slot in (2,3):v,ids=join([(v,ids)]+groups['floor' if slot==2 else 'ceiling'])
            replace_mesh(rx,slot,v,ids)
        (output/(name+'_r76.rx3')).write_bytes(rx.build())
    interior=json.loads((base/'interior_r75.json').read_text(encoding='utf8'));rx=Rx3((base/'interior_r75.rx3').read_bytes())
    for slot,b in enumerate(interior['bindings']):
        if b['material']=='graphic':
            v,ids=read_mesh(rx,slot);v,ids=clip_office(v,ids);replace_mesh(rx,slot,v,ids)
        elif b['material'] in ('secondary_wall_primary','secondary_wall_secondary'):
            v,ids=read_mesh(rx,slot);v,ids=join([(v,ids)]+groups[b['material'].removeprefix('secondary_wall_')]);replace_mesh(rx,slot,v,ids)
    (output/'interior_r76.rx3').write_bytes(rx.build());interior['revision']=76
    (output/'interior_r76.json').write_text(json.dumps(interior,ensure_ascii=False,indent=2),encoding='utf8')
    # Reuse native floor/ceiling and both existing club materials instead of
    # spending four extra component slots on identical materials.
    own={k:v for k,v in groups.items() if k not in ('floor','ceiling','primary','secondary')}
    bindings=write_groups(base/'locker_support_r68.rx3',own,output/'coach_room_r76.rx3')
    layout=json.loads((base/'room_layout_r75.json').read_text(encoding='utf8'))
    def repair(old):
        result=[]
        for o in old:
            # Original furniture/old back wall are replaced. Retain the medical
            # half of shared walls and keep the front partition and door jambs.
            if o['hi'][0]<=LEFT or o['hi'][2]<FRONT:result.append(o);continue
            if o['name'].startswith('Salas / portas abertas') and o['hi'][2]<=1662:result.append(o);continue
            if o['lo'][0]<LEFT:
                clipped=copy.deepcopy(o);clipped['hi'][0]=LEFT;result.append(clipped)
            if o['lo'][2]<FRONT:
                clipped=copy.deepcopy(o);clipped['hi'][2]=FRONT;result.append(clipped)
        return result
    layout['room']['obstacles']=repair(layout['room']['obstacles'])+obstacles
    scenes=[('Sala do treinador · visão geral',[180,175,1710,180,161,2270,75]),
            ('Sala do treinador · quadro tático',[120,180,2370,120,190,2587,69]),
            ('Sala do treinador · desempenho',[525,180,2290,540,180,2587,58]),
            ('Sala do treinador · mercado',[410,177,1880,746,180,1880,57]),
            ('Sala do treinador · destaques',[420,180,2260,746,182,2260,57]),
            ('Sala do treinador · classificação',[-190,177,2320,-200,180,2587,49])]
    layout['medical']['scenes'] += [dict(label=label,pose=pose) for label,pose in scenes]
    layout['revision']=76;layout['coach_bounds']=dict(lo=[-320,0,1561],hi=[750,319,2592])
    (output/'room_layout_r76.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'coach_room_r76.json').write_text(json.dumps(dict(revision=76,bindings=bindings,obstacles=obstacles,bounds=layout['coach_bounds']),ensure_ascii=False,indent=2),encoding='utf8')
    return bindings


def prepare(context,read_asset,add,identity):
    from room_coach_art_r76 import paint
    live=portable.GAME/PREFIX;spec=json.loads((live/'coach_room_r76.json').read_text(encoding='utf8'))
    from room_pes_office import specification
    from room_v3 import enabled
    office=specification(portable.GAME) if enabled(portable.GAME) else None
    if office:spec=dict(spec,bindings=office['shell_bindings'])
    primary,secondary=selected_palette(context,portable.GAME)
    def color(c):return (18,18,18) if max(c)<=8 else c
    images={k:Image.new('RGBA',(8,8),color(v)+(255,)) for k,v in dict(primary=primary,secondary=secondary,dark=(28,33,37),metal=(142,152,158),light=(245,247,241)).items()}
    art_context=dict(context,colors=[[v/255 for v in c] for c in (primary,secondary)])
    if office and office.get('palette_style')=='coach_neutral':
        images['primary']=Image.new('RGBA',(8,8),tuple(office.get('neutral_wall_rgb',[232,229,222]))+(255,))
        images['secondary']=Image.new('RGBA',(8,8),primary+(255,))
        from room_v3 import finish_image
        images['wood']=finish_image(portable.GAME,context['club'],office.get('wood_finish','wood_light'),'cabinet')
        if any(b['material']=='rug' for b in spec['bindings']):
            from room_coach_rug import texture as rug_texture
            images['rug']=rug_texture(primary)
        if any(b['material']=='shirts' for b in spec['bindings']):
            from room_coach_shirts import texture as shirt_texture
            images['shirts']=shirt_texture(context['club'],read_asset)
        art_context['neutral_office']=True
    images['panels']=paint(art_context,read_asset)
    for binding in spec['bindings']:
        key=binding['material']
        if key=='crest':
            crest=f'data/ui/imgassets/crest/light/l{context["club"]}.dds'
            try:read_asset(crest)
            except (OSError,ValueError,FileNotFoundError):continue
            add('coach_crest',PREFIX+'coach_room_r76.rx3',crest,'',identity,True,submesh=binding['submesh'])
            continue
        if key in ('floor','ceiling'):
            texture=PREFIX+('floor_textures_r44.rx3' if key=='floor' else 'ceiling_r72.rx3');name='floor_cm' if key=='floor' else 'ceiling_cm'
        else:
            image=images[key];salt=b'coach-panel-bc1-v1' if key=='panels' else b'coach-rug-bc1-v1' if key=='rug' else b'coach-shirts-bc1-v1' if key=='shirts' else b''
            tag=hashlib.sha256(salt+image.tobytes()).hexdigest()[:18];filename=f'coach_{key}_{context["club"]}_{tag}_r76.rx3';path=live/filename
            if not path.exists():texture_package(image,path,'coach_cm',opaque=key in ('panels','rug','shirts'))
            texture=PREFIX+filename;name='coach_cm'
        add('coach_'+key,PREFIX+'coach_room_r76.rx3',texture,name,identity,submesh=binding['submesh'])

    if office:
        from room_pes_office import prepare as imported_furniture
        imported_furniture(portable.GAME,add,identity)
