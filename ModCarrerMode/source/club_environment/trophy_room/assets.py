"""Editable PNG presentation plus exact native FIFA trophy models/materials."""
from pathlib import Path
from functools import lru_cache
import base64,hashlib,io,json,math,struct,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from . import geometry

BASE=Path(__file__).resolve().parents[1]
for folder in (BASE/'vendor',BASE/'market',BASE/'room'):
    if str(folder) not in sys.path:sys.path.insert(0,str(folder))
from rx3 import Rx3,read_model,diffuse,FORMAT,NAME,MESH,INDEX,VERTEX,TEXTURE,align
from fifa_db import FifaDatabase

PREFIX='data/sceneassets/server16_trophy_room/'


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file() and path.read_bytes()==data:return
    tmp=path.with_name(path.name+'.new');tmp.write_bytes(data);tmp.replace(path)


@lru_cache(maxsize=4)
def catalogue(game,stamp):
    db=FifaDatabase(Path(game),include_all_tables=True)
    teams={int(r['teamid']):r for r in db.rows('teams',['teamid','teamname',*[f'teamcolor{i}{c}' for i in (1,2) for c in 'rgb']])}
    cups={int(r['leagueid']):int(r['trophyid']) for r in db.rows('cz_leagues',['leagueid','trophyid']) if r.get('trophyid')}
    return teams,cups


def club_identity(game,club):
    game=Path(game);teams,cups=catalogue(str(game),(game/'data/db/fifa_ng_db.db').stat().st_mtime_ns)
    row=teams.get(int(club))
    if not row:raise ValueError('Clube não encontrado no catálogo instalado')
    colors=[tuple(max(0,min(255,int(row.get(f'teamcolor{i}{c}') or 0))) for c in 'rgb') for i in (1,2)]
    return dict(club=int(club),name=row['teamname'],colors=colors),cups


def font(size,bold=False):
    import os
    path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/('arialbd.ttf' if bold else 'arial.ttf')
    return ImageFont.truetype(str(path),int(size))


def center(draw,xy,text,size,fill,bold=False,max_width=None):
    while size>10:
        f=font(size,bold)
        if not max_width or draw.textbbox((0,0),text,font=f)[2]<=max_width:break
        size-=1
    draw.text(xy,text,font=f,fill=fill,anchor='mm')


def trophy_thumbnail(game,ident):
    """Centre the cup's visible pixels, rather than its padded DDS canvas."""
    import portable_paths as portable
    for relative in (f'data/ui/imgassets/trophy/t{int(ident)}.dds',f'data/ui/imgassets/trophy256x256/t{int(ident)}.dds'):
        try:
            raw=portable.read_asset(relative)
            with Image.open(io.BytesIO(raw)) as source:image=source.convert('RGBA')
        except (OSError,ValueError,FileNotFoundError):continue
        bbox=image.getchannel('A').point(lambda value:255 if value>8 else 0).getbbox()
        if not bbox:continue
        image=image.crop(bbox);image.thumbnail((232,232),Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',(256,256));canvas.alpha_composite(image,((256-image.width)//2,(256-image.height)//2))
        name=f't{int(ident)}_{hashlib.sha256(raw).hexdigest()[:12]}.png'
        target=Path(game)/PREFIX/'thumbnails'/name
        if not target.is_file():
            stream=io.BytesIO();canvas.save(stream,format='PNG');atomic(target,stream.getvalue())
        return target.relative_to(game).as_posix()
    return ''


def crest(game,club,size=360):
    for kind in ('light','dark'):
        path=Path(game)/f'data/ui/imgAssets/crest/{kind}/l{club}.dds'
        if path.is_file():
            image=Image.open(path).convert('RGBA');image.thumbnail((size,size),Image.Resampling.LANCZOS)
            return image
    raise FileNotFoundError('Escudo do clube não encontrado')


def identity_image(game,identity,custom=False):
    file=Path(game)/'ModCarrerMode/data/trophy_room/custom'/str(identity['club'])/'identity-wall.png'
    if custom and file.is_file():
        with Image.open(file) as im:
            if im.width*im.height>16_777_216:raise ValueError('Imagem custom excede 16 megapixels')
            source=im.convert('RGBA')
            if source.width/source.height>=2:
                return ImageOps.fit(source,geometry.IDENTITY_SIZE,Image.Resampling.LANCZOS)
            # Earlier portrait artwork remains editable and fully visible.
            image=Image.new('RGBA',geometry.IDENTITY_SIZE,(232,234,231,255))
            source.thumbnail(geometry.IDENTITY_SIZE,Image.Resampling.LANCZOS)
            image.alpha_composite(source,((image.width-source.width)//2,(image.height-source.height)//2))
            return image
    image=Image.new('RGBA',geometry.IDENTITY_SIZE,(232,234,231,255));d=ImageDraw.Draw(image)
    logo=crest(game,identity['club'],232);image.alpha_composite(logo,((image.width-logo.width)//2,40))
    center(d,(960,335),'SALA DE TROFÉUS',78,'#23292b',True,1740)
    d.line((706,398,1214,398),fill=identity['colors'][0],width=6)
    center(d,(960,464),identity['name'].upper(),51,'#333b3e',True,1700)
    center(d,(960,552),'CONQUISTAS QUE CONTAM A NOSSA HISTÓRIA',23,'#657174',False,1740)
    return image


def flamengo_wall(game):
    """Flat editable artwork, using the installed crest without changing its drawing."""
    ident,_=club_identity(game,1043);im=identity_image(game,ident);d=ImageDraw.Draw(im)
    d.rectangle((236,420,1684,600),fill=(232,234,231,255))
    center(d,(960,461),'CLUBE DE REGATAS',45,'#252b2d',False,1700)
    center(d,(960,531),'DO FLAMENGO',51,'#252b2d',True,1700)
    # The small red edging is the custom club treatment; the room stays neutral.
    d.rectangle((0,0,12,639),fill='#ae1724');d.rectangle((1907,0,1919,639),fill='#25282a')
    return im


def surface_image(game,material):
    """Reuse the dressing-room door finish, without painting light into it."""
    if material=='leather':
        path=Path(game)/'ModCarrerMode/data/trophy_room/materials/bench-leather.png'
        if path.is_file():
            with Image.open(path) as image:return image.convert('RGBA').resize((512,512),Image.Resampling.LANCZOS)
    if material=='door':
        for relative in ('ModCarrerMode/data/trophy_room/materials/exit-door-graphite.png',
                         'ModCarrerMode/data/club_environment/current_dressing_room/generic/materials/exit-door-graphite.png'):
            path=Path(game)/relative
            if path.is_file():
                with Image.open(path) as image:return image.convert('RGBA').resize((256,768),Image.Resampling.LANCZOS)
    return Image.new('RGBA',(8,8),geometry.MATERIALS[material][0])


def plaque(game,row,index):
    im=Image.new('RGBA',(1024,192),(222,219,207,255));d=ImageDraw.Draw(im)
    d.rectangle((3,3,1020,188),outline='#8f9697',width=3)
    if row is None:
        return im
    for file in (Path(game)/f'data/ui/imgAssets/careerCompetitionIcons/{row["competition"]}.png',
                 Path(game)/f'data/ui/imgAssets/league/l{row["competition"]}.dds'):
        if file.is_file():
            logo=Image.open(file).convert('RGBA');logo.thumbnail((105,105),Image.Resampling.LANCZOS)
            im.alpha_composite(logo,(22+(105-logo.width)//2,(192-logo.height)//2));break
    if row.get('club'):
        logo=crest(game,row['club'],78);im.alpha_composite(logo,(154+(78-logo.width)//2,(192-logo.height)//2))
    center(d,(625,64),row['name'],42,'#263238',True,735)
    years=str(row['year']) if row.get('title_count',1)<3 else f"{row['title_count']} conquistas · {row['first_year']}–{row['last_year']}"
    center(d,(625,133),years+(' · '+row['club_name'] if row.get('club_name') and row.get('title_count',1)<3 else ''),34,'#7e6336',True,735)
    return im


def rx_texture(image,template,name,path,mips=True):
    image=image.convert('RGBA');width,height=image.size;rx=Rx3(Path(template).read_bytes())
    raw=bytearray(rx.get(TEXTURE)[0][:16]);raw[5]=2;count=0
    while True:
        stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5');pixels=stream.getvalue()[128:]
        pitch=max(1,(image.width+3)//4)*16;rows=max(1,(image.height+3)//4)
        raw.extend(struct.pack('<4I',pitch,rows,len(pixels),0));raw.extend(pixels);count+=1
        if not mips or image.size==(1,1):break
        image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    struct.pack_into('<I',raw,0,len(raw));struct.pack_into('<4H',raw,8,width,height,1,count)
    rx.sections=[s for s in rx.sections if s[0]!=TEXTURE];rx.sections.append([TEXTURE,bytes(raw),0])
    for s in rx.sections:
        if s[0]==0x6bd085dc:s[1]=struct.pack('<4I',1,0,0,0)+raw[:16]
    rx.set_names([(TEXTURE,name)]);atomic(path,rx.build());return Path(path)


def pack(v):
    a=np.rint(np.clip(v,-1,1)*511).astype(np.int32)&1023
    return (a[:,0]|a[:,1]<<10|a[:,2]<<20).astype('<u4')


def mesh_file(parts,template,path):
    """Convert final, triangulated geometry, preserving its baked UV coordinates."""
    rx=Rx3(Path(template).read_bytes());vbs=[];ibs=[]
    for part in parts:
        p=np.asarray(part['positions'],dtype=np.float32).reshape(-1,3)
        uv=np.asarray(part['uvs'],dtype=np.float32).reshape(-1,2)
        idx=np.asarray(part['indices'],dtype=np.uint32).reshape(-1,3)
        if len(p)>65535:raise ValueError('Submalha excede 65535 vértices')
        normal=np.asarray(part.get('normals',[]),dtype=np.float32).reshape(-1,3)
        if not len(normal):
            normal=np.zeros_like(p);face=np.cross(p[idx[:,1]]-p[idx[:,0]],p[idx[:,2]]-p[idx[:,0]])
            for k in range(3):np.add.at(normal,idx[:,k],face)
        normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8)
        tangent=np.cross(np.tile([0,1,0],(len(p),1)),normal);bad=np.linalg.norm(tangent,axis=1)<.01
        tangent[bad]=[1,0,0];tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-8)
        out=np.zeros(len(p),dtype=[('p','<f4',3),('n','<u4'),('g','<u4'),('uv','<f2',2)])
        out['p']=p;out['n']=pack(normal);out['g']=pack(tangent);out['uv']=uv
        vb=bytearray(align(16+out.nbytes));struct.pack_into('<4I',vb,0,len(vb),len(p),24,1);vb[16:16+out.nbytes]=out.tobytes();vbs.append(bytes(vb))
        indices=idx.reshape(-1).astype('<u2');ib=bytearray(align(16+indices.nbytes));struct.pack_into('<4I',ib,0,len(ib),len(indices),2,0);ib[16:16+indices.nbytes]=indices.tobytes();ibs.append(bytes(ib))
    # The prop template's packed-normal/f32-position format is retained.
    fmt=rx.get(FORMAT)[0];n=len(vbs)
    rx.sections=[[0x22b2be36,struct.pack('<4I',n,0,0,0)+b''.join(b[:16] for b in ibs),0]]+[[FORMAT,fmt,0] for _ in parts]+[[NAME,rx.get(NAME)[0],0]]+[[INDEX,b,0] for b in ibs]+[[VERTEX,b,0] for b in vbs]+[[MESH,struct.pack('<4I',4,0,0,0),0] for _ in parts]
    rx.set_names([(MESH,f'gallery_part_{i+1}.FxRenderableSimple') for i in range(n)])
    atomic(path,rx.build())


def native_cup(game,ident):
    game=Path(game);model=game/f'data/sceneassets/trophy/trophy_{ident}.rx3'
    texture=model.with_name(f'trophy_{ident}_textures.rx3')
    rx=Rx3(model.read_bytes());parts,_=read_model(rx);tr=Rx3(texture.read_bytes())
    textures=[name for typ,name in tr.names() if typ==TEXTURE]
    cm=next((n for n in textures if n.endswith('_cm')),None)
    if not cm:raise ValueError('Taça sem textura de cor nativa')
    low=np.full(3,np.inf);high=-low
    for p in parts:
        a=np.asarray(p['positions']).reshape(-1,3);low=np.minimum(low,a.min(axis=0));high=np.maximum(high,a.max(axis=0))
    height=high[1]-low[1]
    if height<1:raise ValueError('Taça sem dimensões válidas')
    # Preserve the native asset's proportions AND dimensions. A small cup
    # must not grow to the height of the Libertadores. Only shrink to fit.
    dimensions=high-low
    scale=min(1.,107/height,78/max(1,dimensions[0]),100/max(1,dimensions[2]))
    return dict(id=ident,model=str(model.relative_to(game)).replace('\\','/'),texture=str(texture.relative_to(game)).replace('\\','/'),
                diffuse=cm,normal=next((n for n in textures if n.endswith('_nm')),''),
                coeff=next((n for n in textures if n.endswith('_coeff') or n.endswith('_sk')),''),
                parts=[p['name'].removesuffix('.FxRenderableSimple') for p in parts],
                offset=[float(-(low[0]+high[0])/2),float(-low[1]),float(-(low[2]+high[2])/2)],scale=float(scale),
                native_dimensions_cm=dimensions.tolist(),display_dimensions_cm=(dimensions*scale).tolist(),
                sizing='native size' if scale==1 else 'reduced to fit display case')


def decode_texture(rx,name):
    names=[n for typ,n in rx.names() if typ==TEXTURE];raw=rx.get(TEXTURE)[names.index(name)]
    width,height=struct.unpack_from('<HH',raw,8);fmt=raw[5]
    header=bytearray(128);header[:4]=b'DDS ';struct.pack_into('<7I',header,4,124,0x81007,height,width,0,0,1)
    struct.pack_into('<2I',header,76,32,4);header[84:88]=(b'DXT1',b'DXT3',b'DXT5')[fmt];struct.pack_into('<I',header,108,0x1000)
    return Image.open(io.BytesIO(header+raw[32:])).convert('RGBA')
