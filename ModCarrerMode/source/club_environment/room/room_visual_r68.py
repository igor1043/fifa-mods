"""Stage locker supports and a ceiling with one shared 60 cm module.

Reads installed custom meshes, never native kit textures or career data.
Rebuilding the source scene is unnecessary; names and material slots survive.
"""
from pathlib import Path
import json, struct, math
import numpy as np
from PIL import Image, ImageDraw
from rx3 import Rx3, VERTEX, INDEX, TEXTURE

MODULE = 60.
PREFIX = 'data/sceneassets/server16_dressing_room_20261022/'
VERT = np.dtype([('p','<f4',3),('n','<u4'),('g','<u4'),('uv','<f2',2)])

def packed(v):
    return sum((int(round(max(-1,min(1,float(c)))*511))&1023)<<(i*10) for i,c in enumerate(v))

def box(lo,hi):
    lo,hi=np.array(lo),np.array(hi);vertices=[];ids=[]
    for axis in range(3):
        a,b=(axis+1)%3,(axis+2)%3
        for side in (0,1):
            normal=np.zeros(3);normal[axis]=1 if side else -1
            start=len(vertices)
            for u,v in ((0,0),(1,0),(1,1),(0,1)):
                p=lo.copy();p[axis]=hi[axis] if side else lo[axis];p[a]=hi[a] if u else lo[a];p[b]=hi[b] if v else lo[b]
                tangent=np.zeros(3);tangent[a]=1
                vertices.append((p,packed(normal),packed(tangent),(.75,.5)))
            indices=[0,1,2,0,2,3] if side else [0,2,1,0,3,2]
            ids.extend(start+i for i in indices)
    out=np.zeros(len(vertices),dtype=VERT)
    for i,(p,n,g,uv) in enumerate(vertices):out[i]=(p,n,g,uv)
    return out,np.array(ids,dtype='<u2')

def join(parts):
    vertices=[];indices=[];count=0
    for v,idx in parts:vertices.append(v);indices.append(idx.reshape(-1).astype('<u4')+count);count+=len(v)
    assert count<65536
    return np.concatenate(vertices),np.concatenate(indices).astype('<u2')

def replace_mesh(rx,slot,vertices,indices):
    vb=bytearray(16+vertices.nbytes);struct.pack_into('<4I',vb,0,len(vb),len(vertices),24,1);vb[16:]=vertices.tobytes()
    ib=bytearray(16+indices.nbytes);struct.pack_into('<4I',ib,0,len(ib),len(indices),2,0);ib[16:]=indices.tobytes()
    for kind,data in ((VERTEX,vb),(INDEX,ib)):
        section=[s for s in rx.sections if s[0]==kind][slot];section[1]=bytes(data)
    meta=next(s for s in rx.sections if s[0]==0x22b2be36);data=bytearray(meta[1]);data[16+slot*16:32+slot*16]=ib[:16];meta[1]=bytes(data)

def read_mesh(rx,slot):
    raw=rx.get(VERTEX)[slot];n,stride=struct.unpack_from('<II',raw,4);assert stride==24
    v=np.frombuffer(raw,dtype=VERT,count=n,offset=16).copy()
    raw=rx.get(INDEX)[slot];n=struct.unpack_from('<I',raw,4)[0];idx=np.frombuffer(raw,dtype='<u2',count=n,offset=16).copy()
    return v,idx

def build_ceiling(source,output):
    rx=Rx3(Path(source).read_bytes());centers=[];frames=[];panels=[]
    # Every panel fills two ceiling modules; all edges share the grid origin.
    for z in (-360.,120.,600.,1140.,1620.):
        for x in (-450.,30.,450.):
            if x< -330 and z>942:continue  # medical annex has its own ceiling
            centers.append((x,z))
            frames.append(box((x-29,1317.4,z-59),(x+29,1319.2,z+59)))
            panels.append(box((x-26,1316.9,z-56),(x+26,1317.3,z+56)))
    for slot,new in ((4,frames),(5,panels)):
        v,idx=read_mesh(rx,slot);tri=idx.reshape(-1,3);points=v['p'][tri]
        old_lamp=np.all(points[:,:,1]>1308,axis=1)&np.all(np.abs(points[:,:,0])<730,axis=1)
        medical=np.all(points[:,:,0]< -330,axis=1)&np.all(points[:,:,2]>942,axis=1)
        tri=tri[~(old_lamp&~medical)];used,inverse=np.unique(tri,return_inverse=True)
        parts=[(v[used],inverse.astype('<u2'))]+new
        vertices,ids=join(parts);replace_mesh(rx,slot,vertices,ids)
    v,idx=read_mesh(rx,3);v['uv']=v['p'][:,[0,2]]/MODULE;replace_mesh(rx,3,v,idx)
    Path(output).write_bytes(rx.build())
    return centers

def build_support(source,output):
    # Hook centre is y=213.45,z=32 in each native hanging jersey's local space.
    # One rail and two brackets visibly connect it to the locker back panel.
    pieces=[box((-34,212.2,30.75),(34,214.7,33.25))]
    for x in (-30.,30.):
        pieces += [box((x-1.25,212.2,-4),(x+1.25,214.7,32)),
                   box((x-4,205,-5),(x+4,221,-2))]
    v,idx=join(pieces);rx=Rx3(Path(source).read_bytes())
    # Keep exactly one mesh with the existing 24-byte native room format.
    # Use the room mesh's layout/name directory, then retain only its first slot.
    from rx3 import FORMAT, MESH, NAME
    rx.sections=[[0x22b2be36,struct.pack('<4I',1,0,0,0)+bytes(16),0],
                 [FORMAT,rx.get(FORMAT)[0],0],[NAME,rx.get(NAME)[0],0],
                 [INDEX,bytes(16),0],[VERTEX,bytes(16),0],[MESH,struct.pack('<4I',4,0,0,0),0]]
    rx.set_names([(MESH,'room_part_1.FxRenderableSimple')]);replace_mesh(rx,0,v,idx);Path(output).write_bytes(rx.build())

def ceiling_image():
    image=Image.new('RGBA',(512,512),(230,232,233,255));d=ImageDraw.Draw(image)
    d.rectangle((0,0,511,511),outline=(161,167,172,255),width=3)
    d.line((4,4,508,4),fill=(248,249,250),width=2);d.line((4,4,4,508),fill=(248,249,250),width=2)
    # Subtle acoustic panel texture, deterministic and independent of club color.
    for y in range(15,505,17):
        for x in range(15,505,17):d.point((x,y),fill=(211,215,217,255))
    return image

def stage(game,output):
    import room_native_hanging_20261022 as hanging
    game,output=Path(game),Path(output);output.mkdir(parents=True,exist_ok=True);base=game/PREFIX
    centers=build_ceiling(base/'room_roles_r62.rx3',output/'room_roles_r68.rx3')
    build_support(base/'room_roles_r62.rx3',output/'locker_support_r68.rx3')
    target=output/'ceiling_r68.rx3'
    if target.exists():target.unlink()
    hanging.texture_package(ceiling_image(),target,'ceiling_cm')
    return dict(revision=68,module_cm=MODULE,lights=centers,geometry='room_roles_r68.rx3',ceiling='ceiling_r68.rx3',support='locker_support_r68.rx3')
