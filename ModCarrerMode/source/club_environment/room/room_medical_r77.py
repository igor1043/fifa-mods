"""Integrated sports treatment and rehabilitation room, native RX3 geometry."""
from pathlib import Path
import copy,hashlib,json,math
import numpy as np
from PIL import Image
import portable_paths as portable
from rx3 import Rx3,VERTEX
from room_visual_r68 import VERT,box,join,packed,read_mesh,replace_mesh
from room_interior_r71 import PREFIX,panel
from room_interior_r72 import write_groups,lathe
from room_secondary_wall_r75 import cushion,selected_palette
from room_coach_r76 import clip_office,region
from room_native_hanging_20261022 import texture_package

BACK=2832.


def clip_medical(v,ids):
    # Mirror the already tested rectangle subtraction into the west annex.
    v=v.copy();v['p'][:,0]=-v['p'][:,0]-659
    v,ids=clip_office(v,ids)
    v['p'][:,0]=-v['p'][:,0]-659
    return v,ids


def geometry(rehab_furniture=True):
    groups={k:[] for k in ('primary','secondary','floor','ceiling','dark','metal','white','padding','wood','atlas','glass','crest')};obstacles=[]
    def add(k,shape):groups[k].append(shape)
    def solid(name,lo,hi):obstacles.append(dict(name='Departamento médico R77 / '+name,lo=[lo[0],lo[1]-1000,lo[2]],hi=[hi[0],hi[1]-1000,hi[2]]))
    def color(shape,index):
        v,ids=shape;v=v.copy();v['uv'][:]=((2048+128*index+64)/4096,4064/4096);add('atlas',(v,ids))
    def tube(a,b,r,key='metal',index=None,sides=10):
        a,b=np.array(a,float),np.array(b,float);n=b-a;n/=np.linalg.norm(n);u=np.cross(n,[1,0,0] if abs(n[0])<.8 else [0,0,1]);u/=np.linalg.norm(u);w=np.cross(n,u)
        v=np.zeros((sides+1)*2,dtype=VERT);ids=[]
        for j,c in enumerate((a,b)):
            for s in range(sides+1):
                normal=u*math.cos(s*math.tau/sides)+w*math.sin(s*math.tau/sides);v[j*(sides+1)+s]=(c+normal*r,packed(normal),packed(u),(.5,.5))
        for s in range(sides):a0=s;b0=s+sides+1;ids.extend((a0,a0+1,b0+1,a0,b0+1,b0))
        shape=v,np.array(ids,dtype='<u2')
        if index is None:add(key,shape)
        else:color(shape,index)
    def horizontal(center,width,depth,coords):
        x,y,z=center;u0,v0,u1,v1=coords;v=np.zeros(4,dtype=VERT)
        for i,(a,b,u,t) in enumerate(((-1,-1,u0,v0),(-1,1,u0,v1),(1,1,u1,v1),(1,-1,u1,v0))):v[i]=([x+a*width/2,y,z+b*depth/2],packed([0,1,0]),packed([1,0,0]),(u,t))
        return v,np.array([0,1,2,0,2,3],dtype='<u2')
    def uv(cell):return region(cell,(0,0,2048,960 if cell==7 else 1024))
    # A 7.75 x 12.77 m enclosed annex, keeping the 140 cm entrance in place.
    walls=[((-1119,1000,1545),(-1110,1320,BACK+12)),((-341,1000,1555),(-335,1320,BACK+12)),((-1119,1000,BACK),(-335,1320,BACK+12)),((-1110,1000,1545),(-615,1320,1555)),((-475,1000,1545),(-335,1320,1555))]
    for lo,hi in walls:add('primary',box(lo,hi));solid('parede',lo,hi)
    add('primary',box((-615,1240,1545),(-475,1320,1555)))
    for x,n in ((-1109.6,(1,0,0)),(-341.4,(-1,0,0))):
        add('secondary',panel([x,1120,2195],1270,60,n));add('dark',panel([x,1005,2195],1270,10,n))
    add('secondary',panel([-725,1250,BACK-.4],766,80,(0,0,-1)))
    v,ids=box((-1110,999.8,1555),(-341,1000.4,BACK));v['uv']=v['p'][:,[0,2]]/60;add('floor',(v,ids))
    v,ids=box((-1110,1319.5,1555),(-335,1326,BACK));v['uv']=v['p'][:,[0,2]]/60;add('ceiling',(v,ids))
    for x in (-960,-720,-480):
        for z in (1710,1950,2190,2430,2670):
            add('metal',box((x-60,1318,z-30),(x+60,1319.4,z+30)));add('white',box((x-58,1317.7,z-28),(x+58,1318,z+28)))
    # Identification inside and outside, including the original coach door sign.
    add('atlas',panel([-900,1255,1555.7],350,87.5,(0,0,1),region(5,(0,0,2048,512))))
    add('atlas',panel([-545,1261,1542.2],132,33,(0,0,-1),region(5,(0,0,2048,512))))
    add('atlas',panel([180,1261,1542.2],132,33,(0,0,-1),region(5,(0,512,2048,1024))))
    add('crest',panel([-725,1237,BACK-1],104,114,(0,0,-1)))
    # Administrative desk, with a walnut surface and club-colored drawer bases.
    v,ids=box((-1050,1080,1775),(-815,1086,1860));v['uv']=v['p'][:,[0,2]]/[180,80];add('wood',(v,ids))
    for x in (-1035,-865):
        add('secondary',box((x,1002,1790),(x+40,1079,1855)))
        for y in (1025,1051):add('metal',box((x+10,y,1788),(x+30,y+2,1790)))
    solid('mesa de atendimento',(-1050,1002,1775),(-815,1086,1860))
    def chair(x,z,doctor=False):
        add('padding',cushion((x-28,1043,z-26),(x+28,1050,z+26)))
        back=z+25 if doctor else z-30;add('padding',cushion((x-28,1056,back),(x+28,1133,back+6)))
        for dx in (-23,23):
            for dz in (-21,21):add('metal',box((x+dx-1.5,1001,z+dz-1.5),(x+dx+1.5,1043,z+dz+1.5)))
        solid('cadeira', (x-31,1000,z-32),(x+31,1133,z+32))
    chair(-995,1685);chair(-870,1685);chair(-930,1900,True)
    add('dark',box((-990,1086,1825),(-929,1088,1855)));add('dark',box((-992,1088,1826),(-927,1130,1830)))
    add('atlas',panel([-959.5,1110,1830.2],61,36,(0,0,1),uv(0)))
    for row in range(4):
        for key in range(10):color(box((-988+key*5.5,1088.2,1832+row*5),(-984+key*5.5,1088.8,1835+row*5)),14)
    add('dark',lathe([-916,1086.2,1843],[(0,0),(0,4),(3,4),(4,0)],20))
    for i in range(4):add('atlas',horizontal([-1040+i*.4,1086.4+i*.35,1828],23,35,uv(7)))
    add('primary',box((-900,1086,1792),(-860,1088,1844)));add('atlas',horizontal([-880,1088.2,1818],36,48,uv(7)))
    for x in (-846,-841,-836):tube([x,1086.7,1800],[x,1086.7,1823],.5)
    # Long preparation counter, doors, upper cupboards and an inset steel sink.
    add('white',box((-1107,1003,1970),(-1041,1088,2360)));solid('bancada',(-1107,1003,1970),(-1035,1092,2360))
    for z in range(1972,2350,64):
        add('secondary',box((-1040.8,1011,z),(-1038.5,1082,z+59)));add('metal',box((-1038,1066,z+16),(-1036,1069,z+45)))
    for a,b in ((1970,2074),(2156,2362)):color(box((-1109,1088,a),(-1035,1092,b)),15)
    for a,b in ((-1109,-1096),(-1045,-1035)):color(box((a,1088,2074),(b,1092,2156)),15)
    add('metal',box((-1096,1073,2074),(-1045,1075,2156)))
    for x in (-1096,-1046):add('metal',box((x,1075,2074),(x+1,1090,2156)))
    for z in (2074,2155):add('metal',box((-1096,1075,z),(-1045,1090,z+1)))
    tube([-1090,1091,2115],[-1090,1113,2115],1.4)
    arc=[[-1079+11*math.cos(a),1113+11*math.sin(a),2115] for a in np.linspace(math.pi,0,16)]
    for a,b in zip(arc,arc[1:]):tube(a,b,1.4)
    tube([-1068,1113,2115],[-1068,1106,2115],1.4)
    for z in (1970,2160):
        add('white',box((-1108,1170,z),(-1072,1270,z+155)))
        for zz in (z+2,z+79):add('secondary',box((-1071.8,1172,zz),(-1070,1268,zz+73)));add('metal',box((-1069.8,1205,zz+59),(-1068,1235,zz+61)))
    # Open clean-linen shelving, stacked towels and medical supply boxes.
    add('dark',box((-1106,1093,2320),(-1050,1228,2362)))
    for y in (1095,1136,1177,1225):add('white',box((-1104,y,2320),(-1045,y+3,2362)))
    for y in (1099,1140,1181):
        for i in range(4):add('white',box((-1095,y+i*5,2327),(-1052,y+4+i*5,2356)))
    def bottle(x,y,z,height=25,swatch=12):
        color(lathe([x,y,z],[(0,0),(0,4.5),(height*.65,4.5),(height*.8,2),(height,2),(height,0)],24),swatch)
        add('white',lathe([x,y+height,z],[(0,0),(0,2.5),(3,2.5),(3,0)],20))
    for i in range(6):bottle(-1065,1093,1990+i*13,21+i%2*5,10 if i%2 else 12)
    add('white',box((-1079,1092,2180),(-1048,1118,2222)));add('primary',box((-1047.9,1102,2188),(-1047.5,1108,2215)))
    for z in (2250,2280):color(box((-1093,1093,z),(-1053,1108,z+24)),12)
    bottle(-1066,1093,2229,18,10);tube([-1066,1114,2229],[-1056,1114,2229],1.1)
    # Three parallel treatment couches, with articulated head sections.
    for z in (1830,2130,2430):
        add('metal',box((-668,1066,z-39),(-449,1072,z+39)))
        for x in (-645,-475):
            for zz in (z-29,z+29):add('metal',box((x-3,1002,zz-3),(x+3,1067,zz+3)))
        add('metal',box((-646,1020,z-29),(-473,1024,z+29)))
        add('padding',cushion((-664,1072,z-38),(-509,1082,z+38)))
        v,ids=cushion((-30,-4,-38),(30,4,38));angle=.34;r=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
        v['p']=v['p']@r.T+[-480,1090,z];add('padding',(v,ids))
        for i in range(3):add('white',box((-646,1082.2+i*3,z-23),(-602,1085+i*3,z+23)))
        add('primary',box((-646,1088.4,z+18),(-602,1089,z+21)))
        solid('maca',(-670,1000,z-42),(-446,1110,z+42))
        # Electrotherapy cart, controls, cable and probe; no invented readings.
        for y in (1010,1055,1095):add('white',box((-408,y,z-103),(-355,y+4,z-53)))
        for x in (-404,-361):
            for zz in (z-99,z-59):add('metal',box((x-1.5,1002,zz-1.5),(x+1.5,1096,zz+1.5)));add('dark',lathe([x,1000,zz],[(0,0),(0,3),(5,3),(5,0)],16))
        add('white',box((-403,1099,z-99),(-360,1127,z-60)))
        add('atlas',panel([-403.2,1116,z-79.5],33,17,( -1,0,0),region(6,(0,0,2048,1024))))
        for zz in (z-96,z-61):color(lathe([-405,1103,zz],[(0,0),(0,2),(3,2),(3,0)],16),5)
        cable=[[-401-59*t,1102-32*math.sin(math.pi*t),z-65+55*t] for t in np.linspace(0,1,18)]
        for a,b in zip(cable,cable[1:]):tube(a,b,.65,'dark',sides=7)
        add('white',lathe([-465,1098,z-12],[(0,0),(0,3),(9,3),(10,4),(12,4),(12,0)],20))
        solid('carrinho',(-409,1000,z-104),(-354,1128,z-52))
        sx=-725;sz=z+73;add('padding',lathe([sx,1046,sz],[(0,0),(0,18),(7,18),(9,16),(9,0)],32))
        tube([sx,1004,sz],[sx,1046,sz],2.5)
        for a in np.linspace(0,math.tau,5,endpoint=False):tube([sx,1004,sz],[sx+23*math.cos(a),1004,sz+23*math.sin(a)],1.6)
        solid('banco giratório',(sx-24,1000,sz-24),(sx+24,1055,sz+24))
    # Anatomy charts, dashboard and progression monitor, all with 2:1 mapping.
    for cell,z in ((2,1830),(3,2130),(4,2430)):
        add('dark',panel([-342,1221,z],226,116,(-1,0,0)));add('atlas',panel([-342.3,1221,z],220,110,(-1,0,0),uv(cell)))
    add('dark',panel([-1108,1215,1785],356,181,(1,0,0)));add('atlas',panel([-1107.7,1215,1785],350,175,(1,0,0),uv(0)))
    add('dark',panel([-342,1210,2675],246,126,(-1,0,0)));add('atlas',panel([-342.3,1210,2675],240,120,(-1,0,0),uv(1)))
    # Rehabilitation sector: rubber floor, cable station, bench and mobility kit.
    add('dark',box((-1107,1000.5,2530),(-343,1002.2,BACK-3)))
    for x in range(-1105,-345,80):add('primary',box((x,1002.3,2530),(x+38,1002.6,2533)))
    rehab_start={key:len(value) for key,value in groups.items()};rehab_obstacles=len(obstacles)
    for x in (-1080,-920):add('metal',box((x,1002,2775),(x+6,1240,2819)))
    add('metal',box((-1080,1235,2775),(-914,1242,2819)))
    for y in range(1010,1120,9):add('dark',box((-1032,y,2790),(-962,y+7,2813)))
    for x in (-1065,-935):tube([x,1236,2780],[x,1120,2736],.8,'dark');tube([x-12,1120,2736],[x+12,1120,2736],1.8)
    solid('estação de cabos',(-1090,1000,2765),(-906,1242,2825))
    add('padding',cushion((-1070,1042,2660),(-900,1051,2718)))
    for x in (-1045,-927):add('metal',box((x,1002,2666),(x+5,1042,2713)))
    solid('banco de exercícios',(-1071,1000,2658),(-898,1053,2720))
    add('metal',box((-540,1038,2772),(-352,1043,2823)));add('metal',box((-540,1080,2772),(-352,1085,2823)))
    for x in (-536,-358):add('metal',box((x,1002,2772),(x+4,1084,2823)))
    for x in (-515,-470,-425,-380):
        for y in (1044,1086):
            tube([x-14,y+8,2796],[x+14,y+8,2796],1.8)
            for xx in (x-15,x+15):color(box((xx-4,y+2,2788),(xx+4,y+14,2804)),9)
    solid('halteres',(-542,1000,2770),(-350,1100,2825))
    for x,z,radius in ((-650,2745,38),(-450,2715,28)):
        profile=[(radius*(1-math.cos(a)),radius*math.sin(a)) for a in np.linspace(0,math.pi,25)]
        color(lathe([x,1002.3,z],profile,40),12 if radius==38 else 6)
        solid('bola de estabilidade',(x-radius,1000,z-radius),(x+radius,1002.3+radius*2,z+radius))
    color(box((-810,1002.3,2570),(-735,1005,2770)),5)
    color(lathe([-510,1002.3,2595],[(0,0),(0,26),(6,26),(9,18),(9,0)],32),9)
    color(box((-620,1002.3,2560),(-570,1012,2610)),6)
    if not rehab_furniture:
        for key,count in rehab_start.items():del groups[key][count:]
        del obstacles[rehab_obstacles:]
    # Waste container, clean trays, disposable packs and towel rails add detail.
    for x,z in ((-1090,1920),(-390,2510)):
        add('white',lathe([x,1000.5,z],[(0,0),(0,14),(42,17),(45,17),(45,0)],32));add('secondary',lathe([x,1045.5,z],[(0,0),(0,18),(3,18),(3,0)],32));solid('recipiente',(x-18,1000,z-18),(x+18,1049,z+18))
    for z in (1940,2240):
        tube([-362,1080,z-35],[-362,1080,z+35],1.4)
        add('white',box((-365,1048,z-24),(-361,1080,z+24)))
    # Cabinet glass is a small high-level panel; no opaque plane hides supplies.
    add('glass',panel([-1069.8,1215,2047.5],151,88,(1,0,0)))
    return groups,obstacles


def stage(game,output):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True);base=game/PREFIX;groups,obstacles=geometry()
    for name in ('room_roles','scenery','crest_surfaces','floor_shadows'):
        rx=Rx3((base/(name+'_r76.rx3')).read_bytes())
        for slot in range(len(rx.get(VERTEX))):
            v,ids=read_mesh(rx,slot);v,ids=clip_medical(v,ids)
            if name=='room_roles' and slot in (2,3):v,ids=join([(v,ids)]+groups['floor' if slot==2 else 'ceiling'])
            replace_mesh(rx,slot,v,ids)
        (output/(name+'_r77.rx3')).write_bytes(rx.build())
    spec=json.loads((base/'interior_r76.json').read_text(encoding='utf8'));rx=Rx3((base/'interior_r76.rx3').read_bytes())
    for slot,b in enumerate(spec['bindings']):
        v,ids=read_mesh(rx,slot)
        if b['material']=='graphic':v,ids=clip_medical(v,ids)
        if b['material'] in ('secondary_wall_primary','secondary_wall_secondary'):v,ids=join([(v,ids)]+groups[b['material'].removeprefix('secondary_wall_')])
        replace_mesh(rx,slot,v,ids)
    (output/'interior_r77.rx3').write_bytes(rx.build());spec['revision']=77
    (output/'interior_r77.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
    own={k:v for k,v in groups.items() if k not in ('primary','secondary','floor','ceiling')};bindings=write_groups(base/'locker_support_r68.rx3',own,output/'medical_room_r77.rx3')
    layout=json.loads((base/'room_layout_r76.json').read_text(encoding='utf8'));retained=[]
    for o in layout['room']['obstacles']:
        if o['lo'][0]>=-335 or o['hi'][2]<1561:retained.append(o);continue
        if o['hi'][0]>-335:
            piece=copy.deepcopy(o);piece['lo'][0]=-335;retained.append(piece)
        if o['lo'][2]<1561:
            piece=copy.deepcopy(o);piece['hi'][2]=1561;retained.append(piece)
    layout['room']['obstacles']=retained
    medical=layout['medical'];medical['room_bounds']=dict(lo=[-1110,0,1555],hi=[-335,319,BACK]);medical['obstacles']=obstacles
    medical['navigation']=[[-545,180,1475,-700,160,1770,70],[-750,180,1730,-940,160,1800,70],[-760,180,2110,-520,110,2130,70],[-780,180,2470,-720,140,2720,72],[-740,190,2660,-341,210,2675,60]]
    coach=[s for s in medical['scenes'] if s['label'].startswith('Sala do treinador')]
    scenes=[('entrada',[-545,175,1600,-750,150,2050,76]),('atendimento',[-730,175,1640,-950,155,1810,72]),('situação do elenco',[-760,200,1780,-1108,215,1785,68]),('tratamento',[-760,175,2100,-520,100,2130,72]),('anatomia',[-760,190,2260,-341,225,2130,68]),('reabilitação',[-780,175,2470,-720,140,2720,76]),('recuperação',[-740,200,2660,-341,210,2675,60])]
    medical['scenes']=[dict(label='Departamento médico · '+name,pose=pose) for name,pose in scenes]+coach
    layout['revision']=77;layout['medical_extension_cm']=480
    (output/'room_layout_r77.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'medical_room_r77.json').write_text(json.dumps(dict(revision=77,bindings=bindings,obstacles=obstacles),ensure_ascii=False,indent=2),encoding='utf8')
    return bindings


def prepare(context,read_asset,add,identity):
    from medical_department import prepare as clinical_prepare
    if clinical_prepare(portable.GAME,context,read_asset,add,identity):return
    from room_medical_art_r77 import atlas
    from room_gym_equipment import specification as gym_specification,prepare as gym_prepare
    gym=gym_specification(portable.GAME)
    model=gym['medical_model'] if gym else PREFIX+'medical_room_r77.rx3'
    spec_path=portable.GAME/(gym['medical_spec'] if gym else PREFIX+'medical_room_r77.json')
    live=portable.GAME/PREFIX;spec=json.loads(spec_path.read_text(encoding='utf8'));club=context['club']
    colors=dict(dark=(29,36,43),metal=(162,177,183),white=(235,240,239),padding=(32,51,60),glass=(100,170,184))
    images={k:Image.new('RGBA',(8,8),v+(34 if k=='glass' else 255,)) for k,v in colors.items()}
    y,x=np.mgrid[:256,:1024];grain=np.sin(x*.13+np.sin(y*.028)*2)*5+np.sin(x*.037+y*.004)*3
    wood=np.empty((256,1024,4),dtype='uint8');wood[:,:,:3]=np.clip(np.array([116,86,57])+grain[:,:,None],0,255);wood[:,:,3]=255;images['wood']=Image.fromarray(wood)
    primary,secondary=selected_palette(context,portable.GAME);art_context=dict(context,colors=[[v/255 for v in c] for c in (primary,secondary)])
    def texture(im,key):
        tag=hashlib.sha256(im.tobytes()).hexdigest()[:18];filename=f'medical_{key}_{club}_{tag}_r77.rx3';path=live/filename
        if not path.exists():texture_package(im,path,'medical_cm')
        return PREFIX+filename
    for binding in spec['bindings']:
        key=binding['material']
        if key=='atlas':
            for page in range(context['medical']['pages']):
                size=context['medical'].get('pageSize',6)
                view=dict(art_context,medical=dict(context['medical'],players=context['medical']['players'][page*size:(page+1)*size]));path=texture(atlas(view,read_asset),'atlas')
                add(f'medical_atlas_{page}',model,path,'medical_cm',identity,submesh=binding['submesh'],page=page,pages=context['medical']['pages'],bank=0)
        elif key=='crest':
            path=f'data/ui/imgassets/crest/light/l{club}.dds';name=''
            try:read_asset(path)
            except (FileNotFoundError,OSError):path=texture(Image.new('RGBA',(4,4)),key);name='medical_cm'
            add('medical_crest',model,path,name,identity,True,submesh=binding['submesh'])
        else:add('medical_'+key,model,texture(images[key],key),'medical_cm',identity,key=='glass',submesh=binding['submesh'])
    if gym:gym_prepare(portable.GAME,add,identity)
