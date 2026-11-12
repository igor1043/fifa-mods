"""Fit the existing room walls to V3 cabinet backs without moving any bay.

All coordinates are centimetres. Geometry uses native Y=1000; collision uses
room-local Y=0. The service corridor, doors and both annexes stay in place.
"""
import copy
import numpy as np
from room_visual_r68 import box,read_mesh,replace_mesh
from rx3 import VERTEX

SIDE_END_Z=1543.6
CABINET_END_Z=735.
OLD_SIDE_X=850.
SIDE_INNER_X=835.5
SIDE_SHIFT=OLD_SIDE_X-SIDE_INNER_X
OLD_BACK_Z=-600.
BACK_INNER_Z=-595.5
BACK_SHIFT=BACK_INNER_Z-OLD_BACK_Z


def fit_points(points):
    p=points.copy()
    side=(p[:,2]<=SIDE_END_Z+.001)&(np.abs(p[:,0])>=844)&(np.abs(p[:,0])<=870)
    p[side,0]-=np.sign(p[side,0])*SIDE_SHIFT
    back=(p[:,2]<-595.5)&(np.abs(p[:,0])<=870)
    p[back,2]+=BACK_SHIFT
    return p


def geometry(rx,kind):
    """Edit shell materials only; floor/ceiling grids and annexes survive."""
    from room_v3 import split_at_z
    slots=(0,1) if kind=='roles' else range(len(rx.get(VERTEX))) if kind=='interior' else ()
    if not slots:raise ValueError('Unsupported fitted-shell model')
    changed={}
    for slot in slots:
        v,idx=read_mesh(rx,slot)
        outer=((np.abs(v['p'][:,0])>=844)&(v['p'][:,2]<=SIDE_END_Z)).any()
        rear=(v['p'][:,2]<-595.5).any()
        if not (outer or rear):continue
        v,idx=split_at_z(v,idx,SIDE_END_Z)
        old=v['p'].copy();v['p']=fit_points(old)
        if kind=='interior':
            # The immutable old exit is recognized and removed later by its
            # original coordinates. Move its replacement, not these fixtures.
            from room_exit_door import OLD_LO,OLD_HI
            fixture=((old>=OLD_LO)&(old<=OLD_HI)).all(1)
            v['p'][fixture]=old[fixture]
        count=int((np.abs(v['p']-old)>.001).any(1).sum())
        if count:replace_mesh(rx,slot,v,idx);changed[str(slot)]=count
    return changed


def returns():
    # No return/step: the cabinet wall and service wall share one plane.
    return []


def obstacles(items):
    result=[]
    for original in items:
        parts=[copy.deepcopy(original)]
        if original['name']=='Limite externo' and original['lo'][2]<SIDE_END_Z<original['hi'][2]:
            parts=[copy.deepcopy(original),copy.deepcopy(original)]
            parts[0]['hi'][2]=SIDE_END_Z;parts[1]['lo'][2]=SIDE_END_Z+.01
        for item in parts:
            if item['name'] in ('Limite externo','Sala / parede de fundo'):
                bounds=np.array([item['lo'],item['hi']],dtype=float)
                if bounds[1,2]<=SIDE_END_Z+.001:bounds=fit_points(bounds)
                item['lo'],item['hi']=bounds.tolist()
            # The approved freestanding board replaced these shallow, higher
            # legacy surfaces. Its full footprint is supplied below instead.
            if item['name'] in ('Quadro central / estrutura','Quadro central / superfície','Quadro central / fixadores'):continue
            result.append(item)
    additions=[('ball trolley',[-333,0,296],[-227,100,374]),
               ('next match board',[-125,0,-560],[125,250,-475])]
    names={item['name'] for item in result}
    for name,lo,hi in additions:
        name='Current Dressing Room / '+name
        if name not in names:result.append(dict(name=name,lo=lo,hi=hi))
    return result


def specification():
    return dict(revision=2,side_inner_x_cm=SIDE_INNER_X,side_end_z_cm=SIDE_END_Z,
                back_inner_z_cm=BACK_INNER_Z,cabinet_wall_clearance_cm=1.5,
                cabinet_positions_unchanged=True,service_doorways_unchanged=True)
