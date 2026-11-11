"""Bounded per-submesh lighting probes and small room-only material maps.

Reads original geometry. Creates no per-career cache or copy of native assets.
"""
from pathlib import Path
import struct,math,tempfile
from functools import lru_cache
import numpy as np
from PIL import Image
from rx3 import Rx3,VERTEX,FORMAT,MESH,TEXTURE

PROFILES={
    'matte':(0,0,0,255),
    'wood':(8,8,8,255),
    'metal':(48,48,48,255),
    'glass':(24,24,24,255),
}
PREFIX='data/sceneassets/server16_dressing_room_v3/'


def geometry_probe(model,submesh,read_asset):
    """A submesh can bake world offsets into its vertices; origin is not center."""
    rx=Rx3(read_asset(model));names=[n.removesuffix('.FxRenderableSimple') for kind,n in rx.names() if kind==MESH]
    try:slot=names.index(submesh)
    except ValueError:raise ValueError('Lighting probe submesh missing: '+submesh)
    data=rx.get(VERTEX)[slot];count,stride=struct.unpack_from('<II',data,4)
    if not 0<count<=500000 or not 0<stride<=256 or 16+count*stride>len(data):raise ValueError('Lighting probe buffer outside limits')
    field=next(v for v in rx.get(FORMAT)[slot][16:].split(b'\0')[0].decode().split() if v.startswith('p0:'))
    _,offset,_,_,kind=field.split(':');offset=int(offset,16);half=kind=='4f16';width=2 if half else 4
    if kind not in ('4f16','3f32','4f32') or offset+3*width>stride:raise ValueError('Unsupported lighting probe position')
    points=np.ndarray((count,3),dtype='<f2' if half else '<f4',buffer=data,offset=16+offset,strides=(stride,width)).astype('f4')
    if not np.isfinite(points).all() or np.abs(points).max()>100000:raise ValueError('Invalid lighting probe position')
    lo,hi=points.min(axis=0),points.max(axis=0);center=(lo+hi)*.5;radius=float(np.linalg.norm(hi-lo)*.5)
    return [*map(float,center),max(.1,radius)]


def ensure_materials(game):
    from room_native_hanging_20261022 import texture_package
    game=Path(game);result=[]
    for profile,rgba in PROFILES.items():
        target=game/(PREFIX+'material_'+profile+'_r80.rx3');result.append(str(target))
        if target.is_file():continue
        with tempfile.TemporaryDirectory(prefix='room-material-') as folder:
            sections=[];rx=None
            for name,pixel in (('_nm',(128,128,255,255)),('_coeff',rgba)):
                path=Path(folder)/(name+'.rx3');texture_package(Image.new('RGBA',(4,4),pixel),path,name)
                part=Rx3(path.read_bytes());sections.append(part.get(TEXTURE)[0]);rx=part if rx is None else rx
            rx.sections=[section for section in rx.sections if section[0]!=TEXTURE]+[[TEXTURE,raw,0] for raw in sections]
            for section in rx.sections:
                if section[0]==0x6bd085dc:section[1]=struct.pack('<4I',2,0,0,0)+b''.join(raw[:16] for raw in sections)
            rx.set_names([(TEXTURE,'_nm'),(TEXTURE,'_coeff')]);payload=rx.build()
        target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.new');temp.write_bytes(payload);temp.replace(target)
    return result
