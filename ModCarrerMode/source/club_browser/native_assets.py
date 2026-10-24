"""Convert the posed XI into static native FIFA GameplayProp assets.

Only generated meshes and atlases are written. Templates are read from FIFA's
own asset catalog. No icons, saves, stadiums or existing room files are changed.
"""
from pathlib import Path
import collections, hashlib, io, json, struct, sys, os, shutil, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'club_environment/vendor'))
from rx3 import Rx3, FORMAT, VERTEX, INDEX, MESH, NAME, TEXTURE, align

VERSION=4
SLOTS=96
OPAQUE_SLOTS=64
# Native exporter/WebGL layout: position(0), normal(12), UV(24).
# Swapping normal and UV produces valid triangles with scrambled materials.
STRIDE=np.dtype([('p','<f4',3),('n','<f4',3),('uv','<f4',2)])

def read_model(path):
    raw=Path(path).read_bytes();at=16
    if raw[:8]!=b'FF3D0001' or len(raw)>160*1024*1024:raise ValueError('Modelo dos titulares inválido.')
    nparts,ntex=struct.unpack_from('<II',raw,8)
    if not 1<=nparts<=512 or not 0<=ntex<=256:raise ValueError('Catálogo 3D inválido.')
    def take(n):
        nonlocal at
        if n<0 or at+n>len(raw):raise ValueError('Modelo dos titulares truncado.')
        value=raw[at:at+n];at+=n;return value
    parts=[]
    for _ in range(nparts):
        nv,ni,tex,blend,alpha,*colors=struct.unpack('<IIii7f',take(44))
        if not 0<nv<=58000 or not 0<ni<=3000000 or ni%3 or not -1<=tex<ntex or blend not in (0,1):raise ValueError('Malha dos titulares fora do limite.')
        v=np.frombuffer(take(nv*32),dtype=STRIDE).copy();idx=np.frombuffer(take(ni*4),dtype='<u4').copy()
        if idx.max()>=nv or not np.isfinite(v.view('<f4')).all() or np.abs(v['p']).max()>10000:raise ValueError('Geometria dos titulares inválida.')
        if not all(np.isfinite(colors)) or not 0<=alpha<=1:raise ValueError('Material inválido.')
        parts.append(dict(v=v,idx=idx,tex=tex,blend=bool(blend),alpha=alpha,color=colors[:3],tint=colors[3:],coeff=-1,hair=False))
    textures=[]
    for _ in range(ntex):
        w,h,kind,size=struct.unpack('<4I',take(16))
        expected=w*h*4 if kind==3 else ((w+3)//4)*((h+3)//4)*(8 if kind==0 else 16)
        if not 0<w<=4096 or not 0<h<=4096 or kind>3 or size!=expected:raise ValueError('Textura inválida.')
        textures.append((w,h,kind,take(size)))
    if at<len(raw):
        if take(8)!=b'FFMAT001' or struct.unpack('<I',take(4))[0]!=nparts:raise ValueError('Extensão de material inválida.')
        for p in parts:
            hair,coeff=struct.unpack('<Ii',take(8))
            if hair not in (0,1) or not -1<=coeff<ntex:raise ValueError('Material de cabelo inválido.')
            p['coeff']=coeff if hair else -1;p['hair']=bool(hair)
    if at!=len(raw):raise ValueError('Extensão 3D desconhecida.')
    return parts,textures

def decode(texture):
    w,h,kind,raw=texture
    if kind==3:return Image.frombytes('RGBA',(w,h),raw)
    hdr=bytearray(128);hdr[:4]=b'DDS ';struct.pack_into('<7I',hdr,4,124,0x81007,h,w,len(raw),0,1)
    struct.pack_into('<2I',hdr,76,32,4);hdr[84:88]=(b'DXT1',b'DXT3',b'DXT5')[kind];struct.pack_into('<I',hdr,108,0x1000)
    return Image.open(io.BytesIO(hdr+raw)).convert('RGBA')

def packed(v):
    q=np.rint(np.clip(v,-1,1)*511).astype(np.int32)&1023
    return (q[:,0]|q[:,1]<<10|q[:,2]<<20).astype('<u4')

def geometry(batches,template):
    rx=Rx3(template);vbs=[];ibs=[]
    for v,indices in batches:
        p=v['p'];n=v['n'].copy();n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8);uv=v['uv'];ids=indices.reshape(-1,3).copy()
        sign=np.einsum('ij,ij->i',np.cross(p[ids[:,1]]-p[ids[:,0]],p[ids[:,2]]-p[ids[:,0]]),n[ids].mean(axis=1))
        reverse=sign<-.00001;ids[reverse]=ids[reverse][:,[0,2,1]]
        a,b,c=ids.T;e1=p[b]-p[a];e2=p[c]-p[a];d1=uv[b]-uv[a];d2=uv[c]-uv[a]
        det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0];tangent=(e1*d2[:,1,None]-e2*d1[:,1,None])/np.where(abs(det)>1e-10,det,1)[:,None];tangent[abs(det)<=1e-10]=0
        acc=np.zeros_like(p)
        for k in range(3):np.add.at(acc,ids[:,k],tangent)
        acc-=n*np.sum(acc*n,axis=1,keepdims=True);bad=np.linalg.norm(acc,axis=1)<1e-8;axis=np.zeros_like(p);axis[:,0]=1;axis[abs(n[:,0])>.9]=[0,0,1];acc[bad]=np.cross(axis[bad],n[bad]);acc/=np.maximum(np.linalg.norm(acc,axis=1,keepdims=True),1e-8)
        out=np.zeros(len(p),dtype=[('p','<f2',4),('n','<u4'),('g','<u4'),('uv','<f2',2)])
        out['p'][:,:3]=p;out['p'][:,3]=1;out['n']=packed(n);out['g']=packed(acc);out['uv']=uv
        vb=bytearray(align(16+out.nbytes));struct.pack_into('<4I',vb,0,len(vb),len(p),20,1);vb[16:16+out.nbytes]=out.tobytes();vbs.append(bytes(vb))
        ids=ids.ravel()
        if ids.max()>=65536:raise ValueError('Malha nativa excede 16 bits.')
        ib=bytearray(align(16+ids.size*2));struct.pack_into('<4I',ib,0,len(ib),ids.size,2,0);ib[16:16+ids.size*2]=ids.astype('<u2').tobytes();ibs.append(bytes(ib))
    rx.sections=[[0x22b2be36,struct.pack('<4I',len(vbs),0,0,0)+b''.join(x[:16] for x in ibs),0]]+[[FORMAT,rx.get(FORMAT)[0],0] for _ in vbs]+[[NAME,rx.get(NAME)[0],0]]+[[INDEX,x,0] for x in ibs]+[[VERTEX,x,0] for x in vbs]+[[MESH,struct.pack('<4I',4,0,0,0),0] for _ in vbs]
    rx.set_names([(MESH,f'xi_part_{i+1}.FxRenderableSimple') for i in range(len(vbs))]);return rx.build()

def texture(image,template,name):
    image=image.convert('RGBA');w,h=image.size;rx=Rx3(template);raw=bytearray(rx.get(TEXTURE)[0][:16]);raw[5]=2;mips=0
    while True:
        out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT5');dds=out.getvalue()
        if dds[84:88]!=b'DXT5':raise ValueError('Compressor DXT5 indisponível.')
        pixels=dds[128:];pitch=max(1,(image.width+3)//4)*16;rows=max(1,(image.height+3)//4)
        if len(pixels)!=pitch*rows:raise ValueError('Mip inválido.')
        raw.extend(struct.pack('<4I',pitch,rows,len(pixels),0));raw.extend(pixels);mips+=1
        if image.width==image.height==1:break
        image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    struct.pack_into('<I',raw,0,len(raw));struct.pack_into('<4H',raw,8,w,h,1,mips)
    rx.sections=[s for s in rx.sections if s[0] not in (TEXTURE,0x6bd085dc)];rx.sections.insert(0,[0x6bd085dc,struct.pack('<4I',1,0,0,0)+raw[:16],0]);rx.sections.append([TEXTURE,bytes(raw),0]);rx.set_names([(TEXTURE,name)])
    return rx.build()

def original_texture(source,template,name):
    """Wrap the original compressed pixels. No resize, decode or recompression."""
    w,h,kind,pixels=source
    if kind==3:return texture(decode(source),template,name)
    rx=Rx3(template);raw=bytearray(rx.get(TEXTURE)[0][:16]);raw[5]=kind
    pitch=max(1,(w+3)//4)*(8 if kind==0 else 16);rows=max(1,(h+3)//4)
    raw.extend(struct.pack('<4I',pitch,rows,len(pixels),0));raw.extend(pixels)
    struct.pack_into('<I',raw,0,len(raw));struct.pack_into('<4H',raw,8,w,h,1,1)
    rx.sections=[s for s in rx.sections if s[0] not in (TEXTURE,0x6bd085dc)];rx.sections.insert(0,[0x6bd085dc,struct.pack('<4I',1,0,0,0)+raw[:16],0]);rx.sections.append([TEXTURE,bytes(raw),0]);rx.set_names([(TEXTURE,name)])
    return rx.build()

def convert(model,output,read_asset,material_cache=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);parts,textures=read_model(model)
    keys={};groups=collections.defaultdict(list)
    for p in parts:
        key=(p['tex'],p['coeff'],tuple(p['tint'] if p['tex']>=0 else p['color']),p['alpha'],p['blend'],p['hair'])
        if key not in keys:keys[key]=len(keys)
        p['tile']=keys[key]
    if len(keys)>96:raise ValueError('Muitos materiais para a cena nativa.')
    model_template=read_asset('data/sceneassets/prop/prop_102.rx3');tex_template=read_asset('data/sceneassets/prop/prop_102_textures.rx3')
    coefficient_images={};coefficient_lock=threading.Lock()
    def coverage(coeff,size):
        key=(coeff,size)
        with coefficient_lock:
            if key not in coefficient_images:
                coefficient_images[key]=decode(textures[coeff]).resize(size,Image.Resampling.LANCZOS).getchannel('R')
            return coefficient_images[key]
    seed=hashlib.sha256(b'XI-material-v4\0'+tex_template)
    fingerprints=[hashlib.sha256(struct.pack('<3I',*t[:3])+t[3]).digest() for t in textures] if material_cache else []
    if material_cache:material_cache=Path(material_cache);material_cache.mkdir(parents=True,exist_ok=True)
    def cache_file(entry):
        (tex,coeff,color,alpha,blend,hair),_=entry
        key=seed.copy();key.update(repr((tex>=0,coeff>=0,color,alpha,blend,hair)).encode('ascii'))
        for index in (tex,coeff):
            if index>=0:key.update(fingerprints[index])
        return material_cache/(key.hexdigest()+'.rx3') if material_cache else None
    def link(source,target):
        temp=target.with_name(target.name+f'.{os.getpid()}.{threading.get_ident()}.new')
        try:os.link(source,temp)
        except OSError:shutil.copy2(source,temp)
        os.replace(temp,target)
    def prepare_texture(entry):
        (tex,coeff,color,alpha,blend,hair),i=entry
        direct=tex>=0 and coeff<0 and tuple(color)==(1.,1.,1.) and alpha==1
        size=textures[tex][:2] if tex>=0 else (4,4);target=output/f'atlas_{i}.rx3';cached=cache_file(entry) if material_cache else None
        if cached and cached.is_file():
            # Validate the immutable cached object before the engine can see it.
            blob=cached.read_bytes()
            try:
                rx=Rx3(blob);valid=struct.unpack_from('<I',blob,8)[0]==len(blob) and rx.names()==[(TEXTURE,'xi_cm')]
            except (ValueError,struct.error):valid=False
            if valid:link(cached,target);return i,direct,size
        if direct:
            blob=original_texture(textures[tex],tex_template,'xi_cm');size=textures[tex][:2]
        else:
            im=decode(textures[tex]) if tex>=0 else Image.new('RGBA',(4,4),(255,255,255,255))
            # The same tint/alpha arithmetic as before, evaluated only for 256
            # channel values. PIL applies the tables in native code instead of
            # allocating float64 RGB arrays for every full-resolution hair map.
            lut=[min(255,max(0,int(value*scale))) for scale in color for value in range(256)]+list(range(256))
            im=im.point(lut)
            if coeff>=0:
                mask=[value if 21<=value<166 else 0 for value in range(256)] if blend else [255 if value>=166 else 0 for value in range(256)]
                im.putalpha(coverage(coeff,im.size).point(mask))
            elif blend:im.putalpha(im.getchannel('A').point(np.clip(np.arange(256,dtype='f4')*alpha,0,255).astype('u1').tolist()))
            else:im.putalpha(255)
            blob=texture(im,tex_template,'xi_cm');size=im.size
        if cached:
            temp=cached.with_name(cached.name+f'.{os.getpid()}.{threading.get_ident()}.new');temp.write_bytes(blob);os.replace(temp,cached);link(cached,target)
        else:target.write_bytes(blob)
        return i,direct,size
    # Pillow's native encoders release the GIL. Keep fan-out bounded; FIFA APIs
    # are never called here, and every task owns its image and destination.
    with ThreadPoolExecutor(max_workers=4,thread_name_prefix='xi-material') as pool:
        results=list(pool.map(prepare_texture,keys.items()))
    copied=[i for i,direct,_ in results if direct];sizes=[size for _,_,size in results]
    for p in parts:
        # Preserve original UVs and texture resolution. Only the mesh pose is
        # converted, never the FIFA kit/face layout.
        groups[(p['tile'],p['blend'] or p['hair'])].append((p['v'],p['idx']))
    combined={False:[],True:[]}
    for key,items in sorted(groups.items()):
        vs=[];ids=[];n=0
        for v,idx in items:
            if n+len(v)>58000:
                combined[key[1]].append(((np.concatenate(vs),np.concatenate(ids)),key));vs=[];ids=[];n=0
            vs.append(v);ids.append(idx+n);n+=len(v)
        if vs:combined[key[1]].append(((np.concatenate(vs),np.concatenate(ids)),key))
    batches=[];bindings=[];used_slots=[]
    for transparent,limit in ((False,OPAQUE_SLOTS),(True,SLOTS-OPAQUE_SLOTS)):
        rows=combined[transparent]
        if len(rows)>limit:raise ValueError('Muitas malhas para a cena nativa.')
        for batch,key in rows:used_slots.append(len(batches));batches.append(batch);bindings.append(key)
        for _ in range(limit-len(rows)):
            v=np.zeros(3,dtype=STRIDE);v['n']=[0,1,0];batches.append((v,np.array([0,1,2],dtype='<u4')));bindings.append((0,transparent))
    (output/'geometry.rx3').write_bytes(geometry(batches,model_template))
    (output/'white.rx3').write_bytes(texture(Image.new('RGBA',(4,4),'white'),tex_template,'white_cm'))
    (output/'flat_normal.rx3').write_bytes(texture(Image.new('RGBA',(4,4),(128,128,255,255)),tex_template,'xi_nm'))
    (output/'neutral_coeff.rx3').write_bytes(texture(Image.new('RGBA',(4,4),(0,0,0,255)),tex_template,'xi_coeff'))
    positions=np.concatenate([p['v']['p'] for p in parts]);bounds=np.r_[positions.min(axis=0),positions.max(axis=0)].tolist()
    result=dict(version=VERSION,parts=len(used_slots),used_slots=used_slots,slots=SLOTS,pages=len(keys),bindings=bindings,bounds=bounds,vertices=sum(len(p['v']) for p in parts),original_compressed_textures=copied,texture_sizes=sizes,texture_layout='original FIFA UVs',renderer='FIFA native GameplayProp')
    (output/'assets.json').write_text(json.dumps(result,indent=2),encoding='utf8');return result
