"""Independent table finishes, preserving the existing shape and its stored props."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
import room_appearance as appearance

TOP_Y=1079.


def split(parts):
    groups={'top':[],'base':[]}
    for vertices,indices in parts:
        triangles=indices.reshape(-1,3)
        top=(vertices['p'][triangles][:,:,1]>=TOP_Y-.001).all(1)
        for key,mask in [('top',top),('base',~top)]:
            selected=triangles[mask]
            if not len(selected):continue
            used,inverse=np.unique(selected,return_inverse=True)
            groups[key].append((vertices[used].copy(),inverse.reshape(-1).astype('<u2')))
    if any(not p for p in groups.values()):raise ValueError('Table top/base split did not find both surfaces')
    return groups


def image(game,context,part,choice):
    import room_v3
    game=Path(game);folder=game/appearance.ROOT/'generic/materials'
    if choice=='custom':
        source=appearance.asset(game,context['club'],'table_top')
        if source:return room_v3.editable_image(source)
        choice='default'
    named={'default':'oak_light.png','walnut':'walnut.png','oak':'oak_light.png','stone':'floor_stone.png'}
    if choice in named:return room_v3.editable_image(folder/named[choice])
    rgb={'black':(25,28,30),'white':(235,236,233),'gray':(115,120,124)}.get(choice)
    if choice in ('primary','secondary'):
        rgb=tuple(round(v*255) for v in context['colors'][0 if choice=='primary' else 1])
        rgb=tuple(max(12,v) for v in rgb)
    if rgb is None:raise ValueError('Invalid table finish: '+choice)
    return Image.new('RGBA',(8,8),rgb+(255,))
