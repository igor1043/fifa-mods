"""Club-themed room surfaces. Uses only custom room assets, never career writes.

Art override: ModCarrerMode/data/club_environment/room/clubs/<teamid>/mural.png.
The room layout/locker transforms are unchanged; the exit is a closed door.
"""
from pathlib import Path
import hashlib, io, json, math, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import portable_paths as portable
from rx3 import Rx3, VERTEX, INDEX, TEXTURE
from room_visual_r68 import VERT, box, join, packed, read_mesh, replace_mesh
from room_native_hanging_20261022 import texture_package

REVISION = 71
PREFIX = 'data/sceneassets/server16_dressing_room_20261022/'
ART = 'ModCarrerMode/data/club_environment/room/clubs'
_art_hashes = {}


def palette(colors):
    return [tuple(round(max(0, min(1, c))*255) for c in color) for color in colors]


def ink_for_secondary(rgb):
    # Near-white imported database colors count as white too.
    return (18, 20, 23) if min(rgb) >= 235 else (255, 255, 255)


def font(size):
    return ImageFont.truetype(str(portable.FONTS/'arialbd.ttf'), size)


def sign_image(title, colors, crest=None, symbol=None, size=(2048, 512)):
    primary, secondary = palette(colors)
    im = Image.new('RGBA', size, secondary+(255,)); d = ImageDraw.Draw(im)
    w, h = size; split = int(w*.25); bevel = int(h*.18)
    d.polygon([(0,0),(split+bevel,0),(split-bevel,h),(0,h)], fill=primary)
    d.line([(split+bevel+8,0),(split-bevel+8,h)], fill=primary, width=8)
    d.rectangle((2,2,w-3,h-3), outline=primary, width=max(3,h//30))
    if crest is not None:
        badge=crest.copy();badge.thumbnail((int(split*.70),int(h*.78)),Image.Resampling.LANCZOS)
        im.alpha_composite(badge,((split-badge.width)//2,(h-badge.height)//2))
    right = w-int(h*.9) if symbol else w-50
    x=split+bevel+40; available=right-x
    f=font(int(h*.48))
    while d.textlength(title,font=f)>available and f.size>24:f=font(f.size-1)
    d.text(((x+right)/2,h/2),title,font=f,anchor='mm',fill=ink_for_secondary(secondary))
    if symbol:
        cx=w-h*.48;cy=h/2;radius=h*.29;color=ink_for_secondary(secondary)
        d.rounded_rectangle((cx-radius,cy-radius,cx+radius,cy+radius),radius=8,outline=color,width=max(4,h//55))
        if symbol=='medical':
            a=radius*.65;b=radius*.20
            d.rectangle((cx-a,cy-b,cx+a,cy+b),fill=color);d.rectangle((cx-b,cy-a,cx+b,cy+a),fill=color)
        elif symbol=='exit':
            d.line((cx-radius*.65,cy,cx+radius*.65,cy),fill=color,width=10)
            d.line((cx+radius*.15,cy-radius*.5,cx+radius*.65,cy,cx+radius*.15,cy+radius*.5),fill=color,width=10)
        elif symbol=='water':
            d.polygon([(cx,cy-radius*.8),(cx-radius*.5,cy+radius*.15),(cx+radius*.5,cy+radius*.15)],fill=color)
            d.ellipse((cx-radius*.5,cy-radius*.2,cx+radius*.5,cy+radius*.8),fill=color)
        else:
            d.line((cx,cy-radius*.8,cx,cy+radius*.8),fill=color,width=6)
            d.ellipse((cx-radius*.35,cy-radius*.35,cx+radius*.35,cy+radius*.35),outline=color,width=6)
    return im


def graphic(colors, size=(2048, 512)):
    primary, secondary=palette(colors);w,h=size
    # Clean seamless architectural bands. Broad accents survive native mipmaps
    # without the previous brush scratches, which read as smearing at distance.
    # Four samples per edge pixel preserve diagonal antialiasing without noise.
    base=np.rint(np.array(secondary)*.88+np.array([27,30,33])*.12)
    y,x=np.mgrid[0:h,0:w];coverage=np.zeros((h,w));line=np.zeros((h,w))
    for oy in (.25,.75):
        for ox in (.25,.75):
            phase=((x+ox)/w*2+(y+oy)/h)%1
            coverage+=((phase>=.10)&(phase<.22))*.25
            line+=((phase>=.245)&(phase<.255))*.25
    rgb=np.broadcast_to(base,(h,w,3)).copy()
    rgb=rgb*(1-coverage[:,:,None])+np.array(primary)*coverage[:,:,None]
    edge=np.array(primary)*.45+base*.55
    rgb=rgb*(1-line[:,:,None])+edge*line[:,:,None]
    rgba=np.empty((h,w,4),dtype='uint8');rgba[:,:,:3]=np.clip(rgb,0,255);rgba[:,:,3]=255
    return Image.fromarray(rgba)


def mural_source(game, club):
    root=Path(game)/ART/str(int(club));path=root/'mural.png'
    return path if path.is_file() else None


def make_mural(context, crest, game=None):
    game=Path(game or portable.GAME);path=mural_source(game,context['club'])
    if path:
        with Image.open(path) as source:
            if source.width*source.height>32_000_000:raise ValueError('Mural too large')
            return ImageOps.fit(source.convert('RGBA'),(3072,1024),method=Image.Resampling.LANCZOS)
    im=graphic(context['colors'],(3072,1024));d=ImageDraw.Draw(im)
    if crest is not None:
        badge=crest.copy();badge.thumbnail((650,730),Image.Resampling.LANCZOS);im.alpha_composite(badge,(190,(1024-badge.height)//2))
    text=context['club_name'];f=font(150)
    while d.textlength(text,font=f)>1830 and f.size>30:f=font(f.size-1)
    color=ink_for_secondary(palette(context['colors'])[1]);d.text((1040,400),text,font=f,fill=color)
    d.text((1040,610),'RAÇA  •  UNIÃO  •  CONQUISTA',font=font(60),fill=color)
    return im


def club_sign(context, title, symbol, crest=None, game=None):
    path=Path(game or portable.GAME)/ART/str(context['club'])/f'sign_{symbol}.png'
    if path.is_file():
        with Image.open(path) as source:
            if source.width*source.height>16_000_000:raise ValueError('Sign too large')
            return ImageOps.fit(source.convert('RGBA'),(2048,512),method=Image.Resampling.LANCZOS)
    return sign_image(title,context['colors'],crest,symbol)


def art_stamp(game, club):
    root=Path(game)/ART/str(int(club));digest=hashlib.sha256()
    for name in ('mural.png','hydration.png','sign_medical.png','sign_coach.png','sign_water.png','sign_exit.png'):
        path=root/name
        if path.is_file():
            stat=path.stat();key=(stat.st_size,stat.st_mtime_ns)
            cached=_art_hashes.get(path)
            if cached is None or cached[0]!=key:
                cached=(key,hashlib.sha256(path.read_bytes()).digest());_art_hashes[path]=cached
            digest.update(name.encode());digest.update(cached[1])
    return digest.hexdigest()


def panel(center,width,height,normal=(0,0,1),uv=(0,0,1,1)):
    normal=np.array(normal,dtype=float);up=np.array([0.,1.,0.]);right=np.cross(up,normal)
    center=np.array(center,dtype=float);v=np.zeros(4,dtype=VERT)
    for j,(x,y) in enumerate(((-1,-1),(1,-1),(1,1),(-1,1))):
        v['p'][j]=center+right*x*width/2+up*y*height/2;v['n'][j]=packed(normal);v['g'][j]=packed(right)
        v['uv'][j]=(uv[0] if x<0 else uv[2],uv[3] if y<0 else uv[1])
    return v,np.array([0,1,2,0,2,3],dtype='<u2')


def trim(rx, slot, predicate):
    v,ids=read_mesh(rx,slot);tri=ids.reshape(-1,3);drop=predicate(v['p'][tri])
    kept=tri[~drop]
    if not len(kept):
        # Keep a valid native mesh directory slot below the floor. Empty RX3
        # buffers are unsafe in some FIFA material loaders.
        hidden,ids=box((0,900,0),(.1,900.1,.1));replace_mesh(rx,slot,hidden,ids)
        return int(drop.sum())
    used,inv=np.unique(kept,return_inverse=True)
    replace_mesh(rx,slot,v[used],inv.reshape(-1).astype('<u2'));return int(drop.sum())


def within(points,lo,hi):
    return np.all((points>=np.array(lo)-.04)&(points<=np.array(hi)+.04),axis=(1,2))


def cylinder(center,radius,height,sides=14):
    # Boxes and cylinders use the same native 24-byte vertex format.
    x,y,z=center;rows=[];idx=[]
    for j in range(sides):
        a=j*2*math.pi/sides;b=(j+1)*2*math.pi/sides;start=len(rows)
        normal=[math.cos((a+b)/2),0,math.sin((a+b)/2)]
        for angle,yy in [(a,y),(b,y),(b,y+height),(a,y+height)]:rows.append(([x+math.cos(angle)*radius,yy,z+math.sin(angle)*radius],normal))
        idx.extend(start+k for k in (0,1,2,0,2,3))
    for yy,ny in [(y,-1),(y+height,1)]:
        for j in range(sides):
            a=j*2*math.pi/sides;b=(j+1)*2*math.pi/sides;start=len(rows)
            for p in [[x,yy,z],[x+math.cos(a)*radius,yy,z+math.sin(a)*radius],[x+math.cos(b)*radius,yy,z+math.sin(b)*radius]]:rows.append((p,[0,ny,0]))
            idx.extend([start,start+1,start+2] if ny<0 else [start,start+2,start+1])
    v=np.zeros(len(rows),dtype=VERT)
    for j,(p,n) in enumerate(rows):v[j]=(p,packed(n),packed([0,1,0]),(.5,.5))
    return v,np.array(idx,dtype='<u2')


def stage(game, output):
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True);base=game/PREFIX
    rx=Rx3((base/'room_roles_r68.rx3').read_bytes());removed={}
    # Replace all old ceiling light geometry. The ceiling itself is a single
    # plane with UV grid; removing the old intersecting trims avoids z-fighting.
    for slot in range(len(rx.get(VERTEX))):
        if slot==3:continue
        def remove(p,slot=slot):
            light=np.all(p[:,:,1]>1310,axis=1)
            hydration=within(p,[300,1000,850],[710,1260,941])
            # Narrow black seat stitching: never shoes, seat cushions or legs.
            thin=(np.ptp(p[:,:,1],axis=1)<1.1)&np.all((p[:,:,1]>1058)&(p[:,:,1]<1060),axis=1)
            return light|hydration|(thin if slot==9 else False)
        removed[str(slot)]=trim(rx,slot,remove)
    # The medical annex owns its ceiling; this main footprint does not overlap.
    parts=[box((-756,1320,-600),(756,1326,942)),box((-325,1320,942),(756,1326,1752))]
    cv,ci=join(parts);cv['uv']=cv['p'][:,[0,2]]/60;replace_mesh(rx,3,cv,ci)
    # Flush square LEDs sit exactly inside one tile, with a 1 cm border.
    lights=[]
    for z in [-390,-30,330,690,1050,1410,1650]:
        for x in [-450,30,450]:
            if x< -325 and z>942:continue
            lights.append((x,z))
    for slot,items in [(4,[box((x-30,1318.4,z-30),(x+30,1320,z+30)) for x,z in lights]),
                       (5,[box((x-28,1318.0,z-28),(x+28,1318.3,z+28)) for x,z in lights])]:
        old,ids=read_mesh(rx,slot);new,nidx=join([(old,ids)]+items);replace_mesh(rx,slot,new,nidx)
    medical=Rx3((base/'medical_room_r57.rx3').read_bytes())
    cv,ci=read_mesh(medical,3);cv['uv']=cv['p'][:,[0,2]]/60;replace_mesh(medical,3,cv,ci)
    medical_lights=[(x,z) for x in (-1050.,-690.,-450.) for z in (1050.,1410.,1650.)]
    for slot,margin,low,high in ((8,30,1318.4,1320),(9,28,1318,1318.3)):
        trim(medical,slot,lambda p:np.all(p[:,:,1]>1310,axis=1))
        old,ids=read_mesh(medical,slot)
        new,nidx=join([(old,ids)]+[box((x-margin,low,z-margin),(x+margin,high,z+margin)) for x,z in medical_lights])
        replace_mesh(medical,slot,new,nidx)
    (output/'medical_room_r71.rx3').write_bytes(medical.build())
    # Repaint both already-open door leaves and their trim with a dedicated
    # charcoal material instead of changing the original opening/obstacles.
    door_boxes=[([-482,1002,952],[-476,1228,1060]),([243,1002,952],[249,1228,1060])]
    for slot in range(len(rx.get(VERTEX))):
        if slot in (3,4,5):continue
        trim(rx,slot,lambda p:np.logical_or.reduce([within(p,lo,hi) for lo,hi in door_boxes]))
    rxpath=output/'room_roles_r71.rx3';rxpath.write_bytes(rx.build())
    scenery=Rx3((base/'scenery_r62.rx3').read_bytes())
    for slot in range(len(scenery.get(VERTEX))):
        trim(scenery,slot,lambda p:within(p,[300,1000,850],[710,1260,941])|np.logical_or.reduce([within(p,lo,hi) for lo,hi in door_boxes]))
    (output/'scenery_r71.rx3').write_bytes(scenery.build())
    ceiling=Image.new('RGBA',(512,512),(225,227,226,255));d=ImageDraw.Draw(ceiling)
    d.rectangle((0,0,511,511),outline=(137,146,151),width=3)
    rng=np.random.default_rng(7101)
    for x,y in rng.integers(8,504,(1800,2)):d.point((int(x),int(y)),fill=(211,214,213))
    texture_package(ceiling,output/'ceiling_r71.rx3','ceiling_cm')
    # Dark walnut is a material change only. The original atlas/kit UVs survive.
    for page in (0,1):
        im=decode_texture(base/f'scenery_textures_{page}_r62.rx3');pixels=np.array(im)
        rgb=pixels[:,:,:3].astype(float);wood=(rgb[:,:,0]>rgb[:,:,2]*1.12)&(rgb[:,:,1]>rgb[:,:,2]*1.04)&(rgb[:,:,0]>70)
        rgb[wood]*=[.57,.54,.50];pixels[:,:,:3]=np.clip(rgb,0,255).astype('uint8')
        texture_package(Image.fromarray(pixels),output/f'scenery_textures_{page}_r71.rx3','room_cm')
    groups={}
    def add(key,part):groups.setdefault(key,[]).append(part)
    # Door faces retain their original hinge positions and open leaves.
    for lo,hi in door_boxes:add('charcoal',box(lo,hi))
    for x in [-481,248]:
        add('metal',box((x-.13,1008,963),(x+.13,1033,1050)))
        for z in [956,1057]:add('primary',box((x-.2,1005,z),(x+.2,1225,z+1.2)))
    # Two closed exit leaves on the unused left wall, clear of the locker row.
    for z in [810,889]:
        add('charcoal',box((-750,1001,z-38),(-746,1235,z+38)))
        add('metal',box((-745.8,1064,z-34),(-745.3,1068,z+34)))
        add('metal',box((-745.8,1007,z-34),(-745.5,1031,z+34)))
    for z in [769,930]:add('charcoal',box((-751,1000,z-2),(-744,1240,z+2)))
    add('charcoal',box((-751,1235,767),(-744,1241,932)))
    add('signs',panel([-743.7,1260,850],150,25,(1,0,0),(0,.50,1,.75)))
    # Wall graphics on every side; no opaque plane spans an existing doorway.
    for center,w,n in [([0,1290,-599.5],1510,(0,0,1)),([-749.5,1290,170],1540,(1,0,0)),
                       ([749.5,1290,170],1540,(-1,0,0)),([0,1290,943.5],1500,(0,0,-1)),
                       ([749.5,1290,1345],800,(-1,0,0)),([215,1290,1751.5],1070,(0,0,-1)),
                       ([-324.5,1290,1345],800,(1,0,0)),([-1138.5,1290,1345],800,(1,0,0)),
                       ([-737,1290,1751.5],800,(0,0,-1)),([-335.5,1290,1345],800,(-1,0,0))]:add('graphic',panel(center,w,52,n))
    add('primary',box((-465,1042,940),(105,1265,943)))
    add('mural',panel([-180,1153,939.7],540,180,(0,0,-1)))
    # A second graphic area beside the open coach door, including the crest.
    add('graphic',panel([290,1180,943.3],74,176,(0,0,-1)))
    add('crest',panel([290,1184,942.9],57,66,(0,0,-1)))
    # Hydration counter, wall shelf, towels, cooler jars and a glass-front fridge.
    add('charcoal',box((325,1000,885),(618,1087,939)))
    add('graphic',panel([472,1174,941.7],290,156,(0,0,-1)))
    add('charcoal',box((320,1087,879),(622,1093,941)))
    add('primary',box((325,1083,878.5),(618,1086,879.5)))
    for x in [325,398,471,544]:
        add('metal',box((x+8,1071,878),(x+58,1073,879)))
        add('seam',box((x,1004,878.8),(x+1,1081,879.4)))
    # The fridge front is an opening, not the front face of an opaque box.
    # Separate cabinet shell pieces leave the actual bottle meshes visible.
    for lo,hi in [((630,1000,884),(710,1091,941)),((630,1091,884),(636,1240,941)),
                  ((704,1091,884),(710,1240,941)),((636,1232,884),(704,1240,941)),
                  ((636,1091,937),(704,1232,941))]:add('charcoal',box(lo,hi))
    add('glass',panel([670,1161,883.4],65,136,(0,0,-1)))
    add('metal',box((702,1104,880),(704,1227,883)))
    add('light',box((637,1226,888),(701,1228,892)))
    for y in [1100,1142,1184]:
        add('metal',box((637,y,887),(701,y+2,932)))
        for x in [644,657,670,683,696]:
            add('bottle',cylinder([x,y+3,899],4.5,26));add('secondary',cylinder([x,y+29,899],2.5,4))
            add('crest',panel([x,y+18,894.2],5,7,(0,0,-1)))
    add('charcoal',box((325,1182,911),(615,1186,939)))
    for x in [350,420]:
        for y in [1187,1195,1203]:add('towel',box((x,y,917),(x+58,y+6,937)))
    for x in [350,402]:
        add('primary',cylinder([x,1094,907],20,42));add('towel',cylinder([x,1136,907],21,4))
        add('metal',box((x-2,1097,884),(x+2,1107,887)))
        add('crest',panel([x,1118,886.5],18,23,(0,0,-1)))
    for x in [472,491,510,529,548,567]:
        add('secondary',cylinder([x,1094,906],6,22));add('primary',cylinder([x,1116,906],6.5,4))
    add('signs',panel([472,1255,941.5],285,35,(0,0,-1),(0,.75,1,1)))
    # Make one RX3 slot per shared material; never one draw group per bottle.
    decor=Rx3((base/'locker_support_r68.rx3').read_bytes())
    from rx3 import FORMAT,NAME,MESH
    count=len(groups);fmt=decor.get(FORMAT)[0];name=decor.get(NAME)[0]
    decor.sections=[[0x22b2be36,struct.pack('<4I',count,0,0,0)+bytes(16*count),0]]+[[FORMAT,fmt,0] for _ in groups]+[[NAME,name,0]]+[[INDEX,bytes(16),0] for _ in groups]+[[VERTEX,bytes(16),0] for _ in groups]+[[MESH,struct.pack('<4I',4,0,0,0),0] for _ in groups]
    decor.set_names([(MESH,f'room_part_{j+1}.FxRenderableSimple') for j in range(count)])
    bindings=[]
    for j,(key,parts) in enumerate(groups.items()):
        v,idx=join(parts);replace_mesh(decor,j,v,idx);bindings.append(dict(material=key,submesh=f'room_part_{j+1}'))
    (output/'interior_r71.rx3').write_bytes(decor.build())
    spec=dict(revision=71,bindings=bindings,lights=lights,removed_triangles=removed,layout_changed=False,
              obstacles=[dict(name='Hidratação / bancada r71',lo=[320,0,879],hi=[622,93,941]),dict(name='Hidratação / refrigerador r71',lo=[630,0,884],hi=[710,240,941])])
    (output/'interior_r71.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
    return spec


def decode_texture(path):
    raw=Rx3(Path(path).read_bytes()).get(TEXTURE)[0];w,h=struct.unpack_from('<HH',raw,8);pitch,rows,size,_=struct.unpack_from('<4I',raw,16)
    header=bytearray(128);header[:4]=b'DDS ';struct.pack_into('<7I',header,4,124,0x81007,h,w,size,0,1);struct.pack_into('<2I',header,76,32,4);header[84:88]=b'DXT5';struct.pack_into('<I',header,108,0x1000)
    return Image.open(io.BytesIO(header+raw[32:32+size])).convert('RGBA')


def prepare(context, read_asset, add, identity):
    game=portable.GAME;live=game/PREFIX;spec=json.loads((live/'interior_r71.json').read_text(encoding='utf8'))
    club=context['club'];colors=context['colors'];primary,secondary=palette(colors)
    try:crest=Image.open(io.BytesIO(read_asset(f'data/ui/imgassets/crest/light/l{club}.dds'))).convert('RGBA')
    except (FileNotFoundError,OSError,ValueError):crest=None
    images={}
    atlas=Image.new('RGBA',(2048,2048))
    for j,(title,symbol) in enumerate([('DEPARTAMENTO MÉDICO','medical'),('COMISSÃO TÉCNICA','coach'),('SAÍDA DO VESTIÁRIO','exit'),('HIDRATAÇÃO','water')]):atlas.paste(club_sign(context,title,symbol,crest),(0,j*512))
    images.update(signs=atlas,graphic=graphic(colors),mural=make_mural(context,crest))
    solids=dict(primary=primary,secondary=secondary,charcoal=(21,23,25),metal=(149,155,160),towel=(228,229,223),light=(255,255,248),bottle=(175,207,214),seam=(8,10,12),glass=(38,57,65))
    # Glass is transparent geometry; bottles remain real meshes behind it.
    for name,rgb in solids.items():images[name]=Image.new('RGBA',(8,8),rgb+(55 if name=='glass' else 255,))
    for b in spec['bindings']:
        material=b['material']
        if material=='crest':texture=f'data/ui/imgassets/crest/light/l{club}.dds';texname=''
        else:
            im=images[material];tag=hashlib.sha256(im.tobytes()+str(im.size).encode()).hexdigest()[:16];filename=f'interior_{material}_{club}_{tag}_r71.rx3';dest=live/filename
            if not dest.exists():texture_package(im,dest,'interior_cm')
            texture=PREFIX+filename;texname='interior_cm'
        add('interior_'+material,PREFIX+'interior_r71.rx3',texture,texname,identity,material in ('crest','glass'),submesh=b['submesh'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--game',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();print(json.dumps(stage(a.game,a.output)))
