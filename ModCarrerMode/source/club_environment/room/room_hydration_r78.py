"""Hydration furniture and replaceable club backdrop, isolated from career data."""
from pathlib import Path
import hashlib, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageOps
import room_interior_r71 as prior
from room_visual_r68 import box, join, packed, read_mesh, replace_mesh
from rx3 import Rx3, VERTEX

WIDTH=500.0
HEIGHT=WIDTH/3
WALL_TOP=1316.0
WALL_BOTTOM=WALL_TOP-HEIGHT
CUT_LO=(250,999,1470)
CUT_HI=(752,1318,1543.2)
FRIDGE_BOTTLES=18


def source(game,club):
    from room_club_art import source as club_source
    return club_source(game,club,'hydration_wall')


def backdrop(game,club):
    p=source(game,club)
    if p is None:return Image.new('RGBA',(3072,1024),'white')
    with Image.open(p) as im:
        if im.width*im.height>32_000_000:raise ValueError('Hydration artwork too large')
        # Contain the COMPLETE artwork: never crop or stretch a club's image.
        canvas=Image.new('RGBA',(3072,1024),(20,20,20,255))
        art=ImageOps.contain(im.convert('RGBA'),canvas.size,Image.Resampling.LANCZOS)
        canvas.alpha_composite(art,((canvas.width-art.width)//2,(canvas.height-art.height)//2))
        return canvas


def material_images(context,crest,game):
    primary,secondary=prior.palette(context['colors'])
    atlas=Image.new('RGBA',(2048,2048),(32,35,38,255));d=ImageDraw.Draw(atlas)
    def tile(col,row,title,color):
        x,y=col*512,row*512
        d.rectangle((x,y,x+511,y+511),fill=color)
        if crest is not None:
            badge=ImageOps.contain(crest,(250,270),Image.Resampling.LANCZOS)
            atlas.alpha_composite(badge,(x+(512-badge.width)//2,y+35))
        d.text((x+256,y+393),title,font=prior.font(53),fill='white',anchor='mm')
    for c,(title,color) in enumerate([('ÁGUA',(37,110,161)),('ENERGIA',(184,105,10)),('REPOSIÇÃO',(151,25,44)),('HIDRATAÇÃO',(230,94,8))]):tile(c,0,title,color)
    for c,title in enumerate(['PROTEÍNA','RECUPERAÇÃO','CLUBE','HIDRATAÇÃO']):tile(c,1,title,primary if c==1 else (25,27,29))
    # Quiet, deterministic charcoal stone. No noisy scratches or baked lights.
    stone=np.full((512,512,4),255,dtype=np.uint8)
    y,x=np.mgrid[:512,:512];value=49+((x*17+y*13)%7)
    stone[:,:,:3]=value[:,:,None];stone=Image.fromarray(stone)
    header=prior.sign_image('HIDRATAÇÃO',context['colors'],crest,'water',size=(2048,256))
    custom=source(game,context['club']) is not None
    return dict(hydration_wall=backdrop(game,context['club']),hydration_details=atlas,
                hydration_header=header,counter=stone,bottle_green=Image.new('RGBA',(8,8),(25,28,30,255)),
                fridge_inner=Image.new('RGBA',(8,8),(195,215,222,255)),
                hydration_lower=Image.new('RGBA',(8,8),(55,51,47,255) if custom else (237,237,231,255)),
                fruit_yellow=Image.new('RGBA',(8,8),(245,195,36,255)),
                fruit_red=Image.new('RGBA',(8,8),(176,36,34,255)),
                fruit_green=Image.new('RGBA',(8,8),(61,105,38,255)))


def turned_lathe(center,profile,sides=24):
    from room_interior_r72 import lathe
    v,idx=lathe(center,profile,sides)
    # R72's lathe had inward winding. Correct new props locally, leaving the
    # already installed coach/medical/locker geometry completely untouched.
    return v,idx.reshape(-1,3)[:,[0,2,1]].reshape(-1).copy()


def stage(game,output):
    from room_interior_r72 import write_groups
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True)
    base=game/prior.PREFIX;spec=json.loads((base/'interior_r77.json').read_text(encoding='utf8'))
    rx=Rx3((base/'interior_r77.rx3').read_bytes());groups={}
    for i,b in enumerate(spec['bindings']):
        v,idx=read_mesh(rx,i);tri=idx.reshape(-1,3)
        tri=tri[~prior.within(v['p'][tri],CUT_LO,CUT_HI)]
        if len(tri):
            used,inv=np.unique(tri,return_inverse=True);groups[b['material']]=[(v[used],inv.astype('<u2'))]
        else:groups[b['material']]=[]
    def add(key,part):groups.setdefault(key,[]).append(part)
    def cube(key,lo,hi):add(key,box(lo,hi))
    def panel(key,c,w,h,uv=(0,0,1,1)):add(key,prior.panel(c,w,h,(0,0,-1),uv))
    def lathe(key,c,p,sides=24):add(key,turned_lathe(c,p,sides))
    def label(c,w,h,col,row=0):panel('hydration_details',c,w,h,(col/4,row/4,(col+1)/4,(row+1)/4))
    panel('hydration_wall',(500,(WALL_TOP+WALL_BOTTOM)/2,1540.4),WIDTH,HEIGHT)
    panel('hydration_lower',(500,(1092+WALL_BOTTOM)/2,1540.3),WIDTH,WALL_BOTTOM-1092)
    # Only used for a white fallback wall. Custom artwork already has its title.
    panel('hydration_header',(500,1282,1539.8),470,58.75)
    # Cabinet: inset matte doors, kickboard, edge seam and individual steel pulls.
    cube('charcoal',(340,1003,1481),(682,1090,1542))
    cube('seam',(344,1000,1485),(678,1007,1540))
    for x in (340,397,454,511,568,625):
        cube('cabinet_front',(x+1.5,1009,1478),(x+55.5,1088,1482))
        cube('metal',(x+11,1077,1475.4),(x+45,1079,1478.4))
    cube('primary',(340,1085,1476.8),(682,1088,1480))
    cube('counter',(337,1090,1475),(685,1095,1542))
    # Refrigerator has an OPEN optical aperture, not a full alpha surface that
    # depth-occludes its own contents. Frame/reflection strips suggest glass.
    cube('charcoal',(254,1000,1485),(334,1098,1541))
    for lo,hi in [((254,1098,1485),(259,1235,1541)),((329,1098,1485),(334,1235,1541)),((259,1229,1485),(329,1235,1541)),((259,1098,1537),(329,1229,1541))]:cube('charcoal',lo,hi)
    panel('fridge_inner',(294,1164,1536.8),70,130)
    for x in (259,328):cube('metal',(x,1098,1483),(x+1.5,1230,1485))
    cube('metal',(331,1111,1480.5),(333,1221,1484))
    cube('light',(261,1226,1489),(327,1228,1534))
    for x in (260.5,326.5):panel('glass',(x,1164,1484.2),2,127)
    for row,y in enumerate((1103,1142,1181)):
        for z in (1491,1503,1515,1527):cube('metal',(260,y,z),(328,y+1.1,z+1))
        cube('metal',(260,y,1488),(328,y+1.8,1490))
        for x in (265,276,287,298,309,320):
            key=('drink_red','drink_amber','bottle')[row]
            lathe(key,(x,y+2,1502),[(0,0),(0,3.7),(1,4),(5,4),(6,3.7),(7,4),(19,4),(21,2.1),(26,1.8),(26,0)])
            lathe('cap_white',(x,y+28,1502),[(0,0),(0,2),(2,2),(2,0)])
            label((x,y+16,1497.8),7.8,11,2-row)
    # Proper shelf, brackets and simple recessed diffuser housings.
    cube('charcoal',(350,1193,1508),(680,1197,1538))
    for x in (368,515,660):
        cube('metal',(x,1180,1533),(x+2,1193,1538))
        cube('light',(x-9,1192,1515),(x+9,1193,1524))
    # Two supplemental jars, fitted lids, separate branded front label.
    for x,col,key in ((392,0,'charcoal'),(440,1,'primary')):
        lathe(key,(x,1197,1522),[(0,0),(0,11),(2,13),(24,13),(27,10),(28,10),(28,0)])
        lathe('seam',(x,1225,1522),[(0,0),(0,12),(3,12),(4,10),(4,0)])
        label((x,1211,1508.6),17,22,col,1)
    # White folded towels: thickness, rolled edges and visible fold seams.
    for x in (490,546):
        for y in (1197,1203,1209):
            cube('towel',(x,y,1515),(x+50,y+5.3,1536))
            cube('towel_edge',(x+2,y+1.3,1514.7),(x+48,y+1.8,1515.1))
    cube('charcoal',(610,1197,1510),(670,1221,1537))
    cube('seam',(608,1221,1509),(672,1224,1538))
    for x in (632,647):cube('metal',(x,1224,1521),(x+2,1229,1524))
    cube('metal',(632,1228,1521),(649,1230,1524))
    label((640,1209,1509.7),17,18,2,1)
    # Orange insulated coolers with ribs, anchors, handles, lids and taps.
    for x in (627,573):
        profile=[(0,0),(0,18),(2,21)]+[(float(y),21 if y%4<2 else 20.5) for y in range(3,39)]+[(40,19),(41,0)]
        lathe('orange_plastic',(x,1095,1505),profile,40)
        lathe('cap_white',(x,1136,1505),[(0,0),(0,22),(2,23),(4,22),(5,19),(5,0)],40)
        for side in (-1,1):cube('orange_plastic',(x+side*22-1,1120,1500),(x+side*22+1,1132,1510))
        cube('cap_white',(x-2.2,1102,1480),(x+2.2,1112,1485))
        cube('charcoal',(x-1,1110,1478),(x+1,1114,1484))
        label((x,1120,1483.7),22,25,3)
    # Stacks of real cup rims and club emblems, separated from the fruit tray.
    for x in (526,510):
        for j in range(15):
            y=1095+j*1.1
            lathe('charcoal',(x,y,1505),[(0,0),(0,3),(12,4),(12,3.4),(1,2.5),(1,0)],16)
            lathe('cap_white',(x,y+11.5,1505),[(0,3.4),(0,4),(.7,4),(.7,3.4),(0,3.4)],16)
        label((x,1111,1500.5),5.5,9,2,1)
    cube('metal',(440,1095,1486),(500,1097,1523))
    for lo,hi in [((440,1097,1486),(500,1103,1487)),((440,1097,1522),(500,1103,1523)),((440,1097,1487),(441,1103,1522)),((499,1097,1487),(500,1103,1522))]:cube('metal',lo,hi)
    for x,z in ((448,1498),(462,1514),(480,1506),(491,1515)):
        lathe('fruit_red',(x,1097,z),[(0,0),(1,3),(4,4.5),(7,4),(8,2),(8.2,0)],16)
        cube('charcoal',(x-.3,1105,z-.3),(x+.3,1108,z+.3))
        cube('fruit_green',(x+.4,1105,z),(x+3,1105.7,z+1.7))
    for j in range(5):
        v,idx=turned_lathe((0,0,0),[(0,0),(1,1.1),(4,2),(12,2.3),(18,1.5),(20,0)],12)
        y=v['p'][:,1].copy();v['p'][:,1]=-v['p'][:,2]+1102+j*.8;v['p'][:,2]=y+1492
        for field in ('n','g'):
            values=v[field].astype(np.int64);normal=np.column_stack([(values>>(10*i))&1023 for i in range(3)])
            normal=np.where(normal>=512,normal-1024,normal)/511
            v[field]=[packed((n[0],-n[2],n[1])) for n in normal]
        v['p'][:,0]+=452+j*4+np.sin(y/20*math.pi)*3
        add('fruit_yellow',(v,idx))
    # Squeezes and their molded lids: club colors, not identical green cylinders.
    for x in (350,366,382,398,414,430):
        lathe('bottle_green',(x,1095,1505),[(0,0),(0,5),(2,5.5),(20,5.5),(23,4.5),(25,3),(25,0)],24)
        lathe('primary',(x,1120,1505),[(0,0),(0,4),(3,4),(4,1.5),(7,1.5),(7,0)],24)
        label((x,1109,1499.3),7.5,14,3,1)
    for key in groups:
        if not groups[key]:groups[key]=[box((0,900,0),(.1,900.1,.1))]
    spec['bindings']=write_groups(base/'locker_support_r68.rx3',groups,output/'interior_r78.rx3')
    cooler=Rx3((base/'water_cooler_r75.rx3').read_bytes())
    for slot in range(len(cooler.get(VERTEX))):
        v,idx=read_mesh(cooler,slot);v['p'][:,0]+=438;replace_mesh(cooler,slot,v,idx)
    (output/'water_cooler_r78.rx3').write_bytes(cooler.build())
    spec['obstacles']=[o for o in spec['obstacles'] if not o['name'].startswith('Hidratação /')]+[
        dict(name='Hidratação / bancada r78',lo=[337,0,1475],hi=[685,95,1542]),
        dict(name='Hidratação / refrigerador r78',lo=[254,0,1480],hi=[334,235,1541]),
        dict(name='Hidratação / bebedouro r78',lo=[692,0,1483],hi=[751,140,1540])]
    spec.update(revision=78,cooler_model='water_cooler_r78.rx3',hydration=dict(art='hydration.png',aspect=3,width_cm=WIDTH,height_cm=HEIGHT,bottles=FRIDGE_BOTTLES,full_glass_plane=False))
    (output/'interior_r78.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return spec


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--game',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    print(json.dumps(stage(a.game,a.output)['hydration']))
