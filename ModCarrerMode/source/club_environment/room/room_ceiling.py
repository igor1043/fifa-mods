"""Grid-aligned, recessed ceiling fixtures in native centimetres.

Only room geometry is produced here. Native lights, shadow passes, camera
settings and the closed annex ceilings retain their existing ownership.
"""
import math
import numpy as np
from room_visual_r68 import VERT, packed, box, join, read_mesh, replace_mesh
from room_exit_door import cylinder

MODULE = 60.
LIGHTS = tuple((x, z) for x in (-450., 30., 450.) for z in (-300., 240., 780., 1320.))
SUPPLY = ((-210., 30.), (-210., 1290.))
RETURN = ((270., 930.),)
SPRINKLERS = tuple((x, z) for x in (-570., 150., 570.) for z in (540., 1140.))


def openings():
    return [(x-30, x+30, z-60, z+60) for x,z in LIGHTS] + [
        (x-30, x+30, z-30, z+30) for x,z in SUPPLY+RETURN]


def horizontal(x0, x1, z0, z1, y, up=False):
    v = np.zeros(4, dtype=VERT)
    v['p'] = [(x0,y,z0), (x1,y,z0), (x1,y,z1), (x0,y,z1)]
    v['n'] = packed((0,1 if up else -1,0)); v['g'] = packed((1,0,0))
    v['uv'] = v['p'][:,[0,2]]/MODULE
    return v, np.array((0,2,1,0,3,2) if up else (0,1,2,0,2,3), dtype='<u2')


def tiles(y, end):
    """One world grid, including partial border tiles, with real openings."""
    parts=[]
    for x0 in np.arange(-900., 850., MODULE):
        for z0 in np.arange(-600., end, MODULE):
            lo,hi=max(-850.,x0),min(850.,x0+MODULE)
            back,front=z0,min(end,z0+MODULE)
            if lo>=hi or back>=front:continue
            cx,cz=(lo+hi)/2,(back+front)/2
            if any(a<cx<b and c<cz<d for a,b,c,d in openings()):continue
            parts.append(horizontal(lo,hi,back,front,y))
            parts.append(horizontal(lo,hi,back,front,y+6,True))
    return join(parts)


def replace_main_ceiling(rx, y, end):
    """Replace the main roof only; retain every annex triangle byte-for-byte."""
    vertices,ids=read_mesh(rx,3);tri=ids.reshape(-1,3);p=vertices['p'][tri]
    main=(p[:,:,2]<=end+.001).all(1) & (p[:,:,1]>=1310.).all(1)
    kept=tri[~main]
    if not main.any():raise ValueError('Main ceiling was not found')
    parts=[]
    if len(kept):
        used,inverse=np.unique(kept,return_inverse=True)
        parts.append((vertices[used],inverse.reshape(-1).astype('<u2')))
    parts.append(tiles(y,end));replace_mesh(rx,3,*join(parts))
    return int(main.sum())


def geometry(y):
    groups={key:[] for key in ('paint','metal','diffuser','vent','sprinkler_glass')}
    def solid(key,lo,hi):groups[key].append(box(lo,hi))
    def frame(x,z,half_x,half_z,inside_x,inside_z,bottom,top,key='metal'):
        for side in (-1,1):
            a,b=sorted((side*inside_x,side*half_x))
            solid(key,(x+a,bottom,z-half_z),(x+b,top,z+half_z))
            a,b=sorted((side*inside_z,side*half_z))
            solid(key,(x-inside_x,bottom,z+a),(x+inside_x,top,z+b))
    for x,z in LIGHTS:
        # A 60x120 opening, 62x122 trim, reflective deep housing and opal lens.
        frame(x,z,31,61,27.5,57.5,y-.8,y+.4,'paint')
        frame(x,z,29.7,59.7,27.8,57.8,y+.4,y+6.4)
        solid('vent',(x-27.8,y+6.2,z-57.8),(x+27.8,y+6.5,z+57.8))
        solid('diffuser',(x-27.4,y+4.8,z-57.4),(x+27.4,y+5.1,z+57.4))
        # Louvers have depth and an actual silhouette, not a grid texture.
        for dz in (-42.,-28.,-14.,0.,14.,28.,42.):
            solid('metal',(x-27.4,y+.7,z+dz-.4),(x+27.4,y+4.65,z+dz+.4))
        solid('metal',(x-.4,y+.7,z-57.4),(x+.4,y+4.65,z+57.4))
        for dx,dz in ((-29,0),(29,0)):
            groups['metal'].append(cylinder((x+dx,y-.9,z+dz),.42,.2,axis=1,sides=8))
    for x,z in SUPPLY+RETURN:
        frame(x,z,31,31,27,27,y-.7,y+.4,'paint')
        solid('vent',(x-29.7,y+5.7,z-29.7),(x+29.7,y+6,z+29.7))
        frame(x,z,29.7,29.7,27,27,y+.4,y+5.7,'paint')
        if (x,z) in SUPPLY:
            # Four-way square diffuser, nested vanes stepped into the opening.
            for ring in range(4):
                extent=25.-ring*5.5
                frame(x,z,extent,extent,extent-1.1,extent-1.1,y+.6+ring*.9,y+1.5+ring*.9,'paint')
            solid('paint',(x-4.4,y+4.4,z-4.4),(x+4.4,y+4.7,z+4.4))
        else:
            for dz in np.arange(-24.,24.1,4.):
                solid('metal',(x-26.4,y+.5,z+dz-.45),(x+26.4,y+4.4,z+dz+.45))
            solid('metal',(x-.45,y+.4,z-26.4),(x+.45,y+4.4,z+26.4))
    for x,z in SPRINKLERS:
        groups['paint'].append(cylinder((x,y-.25,z),4.7,.5,axis=1,sides=20))
        groups['metal'].append(cylinder((x,y-1.4,z),1.05,2.1,axis=1,sides=12))
        for side in (-1,1):
            solid('metal',(x+side*1.6-.25,y-5.8,z-.35),(x+side*1.6+.25,y-2.3,z+.35))
        groups['sprinkler_glass'].append(cylinder((x,y-3.7,z),.43,2.3,axis=1,sides=10))
        groups['metal'].append(cylinder((x,y-6,z),2.1,.3,axis=1,sides=16))
        for angle in (0,math.pi/2):
            dx,dz=math.cos(angle)*2.5,math.sin(angle)*2.5
            solid('metal',(x-dx-.12,y-6.3,z-dz-.12),(x+dx+.12,y-6.1,z+dz+.12))
    return groups


def specification(y):
    return dict(module_cm=MODULE,ceiling_y=y,lights=[list(p) for p in LIGHTS],
                supply=[list(p) for p in SUPPLY],air_return=[list(p) for p in RETURN],
                sprinklers=[list(p) for p in SPRINKLERS],recessed=True,
                native_lighting_changed=False)
