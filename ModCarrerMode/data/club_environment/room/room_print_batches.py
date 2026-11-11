"""Batch locker decals without reducing their original pixel resolution."""
from pathlib import Path
import hashlib,math,struct
import numpy as np
from PIL import Image
from rx3 import Rx3,MESH,FORMAT,VERTEX,INDEX
from room_visual_r68 import VERT,read_mesh,packed
from room_interior_r72 import write_groups
from room_native_hanging_20261022 import texture_package

PREFIX='data/sceneassets/server16_dressing_room_v3/shared/'
LIMIT=4096

def mesh(rx,slot):
    raw=rx.get(VERTEX)[slot];count,stride=struct.unpack_from('<II',raw,4)
    if stride==24:return read_mesh(rx,slot)
    fmt=rx.get(FORMAT)[slot][16:].split(b'\0')[0]
    if stride!=20 or b'p0:00:00:0001:4f16' not in fmt:raise ValueError('Unrecognized locker print vertex layout')
    dtype=np.dtype([('p','<f2',4),('n','<u4'),('g','<u4'),('uv','<f2',2)])
    source=np.frombuffer(raw,dtype=dtype,count=count,offset=16)
    v=np.zeros(count,dtype=VERT);v['p']=source['p'][:,:3]
    for field in ('n','g','uv'):v[field]=source[field]
    raw=rx.get(INDEX)[slot];count=struct.unpack_from('<I',raw,4)[0]
    return v,np.frombuffer(raw,dtype='<u2',count=count,offset=16).copy()

def pages(items):
    """Shelf pack unchanged images; trim each page to power-of-two dimensions."""
    result=[];page=[];x=y=row_h=0
    for item in items:
        w,h=item['image'].size
        if not (0<w<=LIMIT and 0<h<=LIMIT):raise ValueError('Locker print exceeds atlas dimensions')
        if x+w>LIMIT:x=0;y+=row_h;row_h=0
        if y+h>LIMIT:result.append(page);page=[];x=y=row_h=0
        page.append((item,x,y));x+=w;row_h=max(row_h,h)
    if page:result.append(page)
    return result

def transformed(vertices,matrix,rect,size):
    out=vertices.copy();m=np.asarray(matrix,dtype=float).reshape(4,4).T.copy();m[0,3]-=100000
    out['p']=vertices['p']@m[:3,:3].T+m[:3,3]
    for field,normal in [('n',True),('g',False)]:
        raw=vertices[field].astype(np.int64)
        xyz=np.stack([(raw>>shift)&1023 for shift in (0,10,20)],axis=1)
        xyz=np.where(xyz>=512,xyz-1024,xyz)/511.
        xyz=xyz@(np.linalg.inv(m[:3,:3]) if normal else m[:3,:3].T)
        xyz/=np.maximum(np.linalg.norm(xyz,axis=1,keepdims=True),1e-8)
        out[field]=np.array([packed(v) for v in xyz],dtype='<u4')
    x,y,w,h=rect;aw,ah=size
    # Half-texel inset isolates adjacent tiles at close range. No resizing,
    # clipping, font substitution or change to the original kit hotspot.
    uv=vertices['uv'].astype(float)
    out['uv'][:,0]=(x+.5+np.clip(uv[:,0],0,1)*(w-1))/aw
    out['uv'][:,1]=(y+.5+np.clip(uv[:,1],0,1)*(h-1))/ah
    return out

def prepare(game,kind,items,read_asset,add,identity,alpha):
    game=Path(game);folder=game/PREFIX;folder.mkdir(parents=True,exist_ok=True)
    for number,page in enumerate(pages(items)):
        width=2**math.ceil(math.log2(max(x+i['image'].width for i,x,y in page)))
        height=2**math.ceil(math.log2(max(y+i['image'].height for i,x,y in page)))
        atlas=Image.new('RGBA',(width,height));parts=[];signature=hashlib.sha256(b'locker-print-batches-v1')
        for item,x,y in page:
            im=item['image'];atlas.paste(im,(x,y))
            raw=read_asset(item['model']);rx=Rx3(raw)
            names=[n.removesuffix('.FxRenderableSimple') for t,n in rx.names() if t==MESH]
            vertices,indices=mesh(rx,names.index(item.get('submesh','room_part_1')))
            v=transformed(vertices,item['matrix'],(x,y,*im.size),(width,height));parts.append((v,indices))
            signature.update(v.tobytes());signature.update(indices.tobytes())
        signature.update(atlas.tobytes());tag=signature.hexdigest()[:16]
        stem=f'prints_{kind}_{tag}';model=folder/(stem+'.rx3');texture=folder/(stem+'_textures.rx3')
        if not model.exists():write_groups(game/PREFIX/'locker_support_r68.rx3',{'print':parts},model)
        if not texture.exists():texture_package(atlas,texture,'print_cm')
        add(f'{kind}_batch_{number}',PREFIX+model.name,PREFIX+texture.name,'print_cm',identity,alpha,'room_part_1')
