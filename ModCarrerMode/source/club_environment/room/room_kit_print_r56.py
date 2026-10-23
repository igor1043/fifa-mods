import portable_paths as portable
"""Name placement uses the same kit RX3 hotspots as native jersey materials."""
import struct,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from room_scene_native_assets_20261022 import DTYPE,ROOT,LIVE
from room_precise_mesh_r49 import precise_prop_file

def kit_hotspots(rx):
    sections=rx.get(0xf55b1a1a)
    if len(sections)!=1:return {}
    raw=sections[0];offset=16;result={}
    def string():
        nonlocal offset
        end=raw.index(0,offset);text=raw[offset:end].decode('ascii');offset=end+1;return text
    try:
        for _ in range(raw[5]):
            group=string();count=raw[offset];offset+=1
            if count>32:raise ValueError('Hotspot count')
            result[group]={}
            for _ in range(count):
                name=string();values=struct.unpack_from('<4f',raw,offset);offset+=16
                if not all(math.isfinite(v) and -2<=v<=2 for v in values):raise ValueError('Hotspot bounds')
                result[group][name]=values
    except (ValueError,IndexError,struct.error,UnicodeError):return {}
    return result

def native_name_surface(shirt,indices,rect):
    tri=indices.reshape(-1,3);uv=shirt['uv'][tri];positions=shirt['p'][tri]
    a,b,c=uv[:,0],uv[:,1],uv[:,2]
    den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);good=abs(den)>1e-9
    def project(u,v):
        x=np.divide((b[:,1]-c[:,1])*(u-c[:,0])+(c[:,0]-b[:,0])*(v-c[:,1]),den,out=np.zeros_like(den),where=good)
        y=np.divide((c[:,1]-a[:,1])*(u-c[:,0])+(a[:,0]-c[:,0])*(v-c[:,1]),den,out=np.zeros_like(den),where=good);z=1-x-y
        hit=good&(x>=-1e-5)&(y>=-1e-5)&(z>=-1e-5)
        if not hit.any():return None
        p=positions[hit,0]*x[hit,None]+positions[hit,1]*y[hit,None]+positions[hit,2]*z[hit,None]
        return p[p[:,2].argmax()]
    l,t,r,bottom=rect
    corners=[project(u,v) for u,v in ((l,t),(r,t),(r,bottom),(l,bottom))]
    if any(p is None for p in corners):raise ValueError('Kit name hotspot outside native jersey UV')
    # Preserve readable axes on the back of the hanging jersey.
    if corners[1][0]<corners[0][0]:l,r=r,l
    if (corners[0][1]+corners[1][1])<(corners[2][1]+corners[3][1]):t,bottom=bottom,t
    vertices=[];faces=[]
    for y in range(8):
        for x in range(24):
            coords=[(x/24,y/8),((x+1)/24,y/8),((x+1)/24,(y+1)/8),(x/24,(y+1)/8)];points=[project(l+(r-l)*u,t+(bottom-t)*v) for u,v in coords]
            if any(p is None for p in points):continue
            normal=np.cross(points[3]-points[0],points[1]-points[0]);normal/=max(1e-8,np.linalg.norm(normal))
            if normal[2]<0:normal=-normal
            start=len(vertices)
            for p,coord in zip(points,coords):vertices.append((p+normal*.35,coord,normal))
            faces.extend(start+i for i in (0,1,2,0,2,3))
    if not faces:raise ValueError('Empty native name surface')
    out=np.zeros(len(vertices),dtype=DTYPE)
    for i,(p,uv,n) in enumerate(vertices):out['p'][i]=p;out['uv'][i]=uv;out['n'][i]=n
    return out,np.array(faces,dtype='<u4')

def print_model(club,typ,rect,part):
    from room_native_hanging_20261022 import source_shirt
    if rect is None:return None,None
    if abs(rect[2]-rect[0])<1e-6 or abs(rect[3]-rect[1])<1e-6:return None,None
    tag=hashlib.sha256(struct.pack('<4f',*rect)).hexdigest()[:12];name=f'native_{part}_surface_{club}_{typ}_{tag}_r61.rx3';path=LIVE/name
    shirt,ids,_=source_shirt(typ)
    if not path.exists():precise_prop_file([native_name_surface(shirt,ids,rect)],ROOT/'assets'/name)
    return 'data/sceneassets/server16_dressing_room_20261022/'+name,list(rect)

def name_model(club,typ,kit_rx):
    return print_model(club,typ,kit_hotspots(kit_rx).get('jersey',{}).get('name'),'name')

def number_models(club,typ,kit_rx):
    """The native back-number rectangle contains two digit cells, not one.

    A single digit occupies the centre cell. All bounds remain in the kit's
    original UV space; the hanging mesh must never supply an XYZ print offset.
    """
    rect=kit_hotspots(kit_rx).get('jersey',{}).get('numberback')
    if rect is None:return {}
    l,t,r,b=rect;mid=(l+r)/2;quarter=(r-l)/4
    return {slot:print_model(club,typ,box,'number_'+str(slot))
            for slot,box in ((4,(mid-quarter,t,mid+quarter,b)),
                             (5,(l,t,mid,b)),(6,(mid,t,r,b)))}

def name_stamp(name,font_bytes,color,rect):
    """Fill the kit hotspot with the selected native font, without UI margins.

    Keep glyph height constant for long names: only their horizontal extent
    is condensed to fit, rather than moving or shrinking the name on the kit.
    """
    import io
    name=' '.join(name.upper().split())
    font=ImageFont.truetype(io.BytesIO(font_bytes),256)
    box=font.getbbox(name)
    if not name or box[2]<=box[0] or box[3]<=box[1]:return None
    glyph=Image.new('RGBA',(box[2]-box[0],box[3]-box[1]),(0,0,0,0))
    ImageDraw.Draw(glyph).text((-box[0],-box[1]),name,font=font,fill=tuple(color)+(255,))
    ratio=abs((rect[2]-rect[0])/(rect[3]-rect[1]));height=128
    width=max(4,min(4096,2**math.ceil(math.log2(ratio*height))))
    target=Image.new('RGBA',(width,height),(0,0,0,0))
    scaled_width=min(width,max(1,round(glyph.width/glyph.height/ratio*width)))
    glyph=glyph.resize((scaled_width,height),Image.Resampling.LANCZOS)
    target.alpha_composite(glyph,((width-scaled_width)//2,0))
    return target

def plate_lines(name,draw,width,font):
    name=' '.join(name.split())
    if draw.textlength(name,font=font)<=width:return [name]
    words=name.split();choices=[]
    for i in range(1,len(words)):
        pair=[' '.join(words[:i]),' '.join(words[i:])]
        choices.append((max(draw.textlength(line,font=font) for line in pair),pair))
    return min(choices,key=lambda item:item[0])[1] if choices else [name]

def locker_plate(name,colors,crest=None):
    im=Image.new('RGBA',(1024,256),(239,243,246,255));d=ImageDraw.Draw(im);primary=tuple(round(v*255) for v in colors[0]);d.rectangle((0,0,22,255),fill=primary);d.line((30,251,1024,251),fill=(130,146,154),width=4)
    left=54
    if crest is not None:
        crest=crest.copy();crest.thumbnail((148,184),Image.Resampling.LANCZOS);im.alpha_composite(crest,(46+(148-crest.width)//2,(256-crest.height)//2));left=220
    name_font=ImageFont.truetype(str(portable.FONTS/'arialbd.ttf'),79);width=986-left
    lines=plate_lines(name,d,width,name_font)
    while max(d.textlength(line,font=name_font) for line in lines)>width and name_font.size>25:
        name_font=name_font.font_variant(size=name_font.size-1);lines=plate_lines(name,d,width,name_font)
    line_height=98 if len(lines)>1 else 110;y=(256-line_height*len(lines))//2
    for line in lines:
        d.text((left+width/2,y+line_height/2),line,font=name_font,anchor='mm',fill=(17,35,45));y+=line_height
    return im
