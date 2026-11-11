"""Single hinged room doors, sharing the exit door's finish selection.

Keep the existing 90-degree inward swing and the 130 cm openings. Imported
office furniture, medical equipment and their live information remain intact.
"""
import copy
import numpy as np
from room_visual_r68 import box, packed, read_mesh, replace_mesh

DOORS=(('coach',180.),('medical',-545.))
WIDTH=126.
BOTTOM,TOP=1001.5,1233.5
HINGE_Z=1552.
TURN=np.array([[0.,0.,1.],[0.,1.,0.],[-1.,0.,0.]])


def unpack(values):
    channels=np.stack([(values.astype(np.int64)>>(a*10))&1023 for a in range(3)],axis=1)
    return np.where(channels>=512,channels-1024,channels)/511.


def swing(shape,cx):
    v,idx=shape;v=v.copy()
    v['p']=v['p']@TURN.T+[cx+66.,0.,HINGE_Z]
    for key in ('n','g'):
        vectors=unpack(v[key])@TURN.T
        v[key]=[packed(vector) for vector in vectors]
    return v,idx.copy()


def geometry():
    from room_exit_door import cylinder
    groups={key:[] for key in ('annex_leaves','frame','metal','kick')}
    for name,cx in DOORS:
        local={key:[] for key in ('annex_leaves','metal','kick')}
        def solid(key,lo,hi):local[key].append(box(lo,hi))
        v,idx=box((-WIDTH,BOTTOM,-2.2),(0.,TOP,2.2))
        v['uv'][:,0]=-v['p'][:,0]/WIDTH
        back=unpack(v['n'])[:,2]>.9
        v['uv'][back,0]=(v['p'][back,0]+WIDTH)/WIDTH
        v['uv'][:,1]=(TOP-v['p'][:,1])/(TOP-BOTTOM)
        local['annex_leaves'].append((v,idx))
        for side in (-1,1):
            # A conventional lever and lock on each side of the one-piece leaf.
            local['metal'].append(cylinder((-113,1105,side*2.8),2.8,.7,axis=2,sides=16))
            local['metal'].append(cylinder((-113,1105,side*4.7),.9,3.,axis=2))
            local['metal'].append(cylinder((-107.5,1105,side*6.2),.9,11.,axis=0))
            local['metal'].append(cylinder((-113,1096,side*2.8),1.8,.7,axis=2))
            local['kick'].append(cylinder((-113,1096,side*3.22),.65,.2,axis=2,sides=8))
            z0,z1=sorted((side*2.35,side*2.65))
            solid('metal',(-WIDTH+4.,1007.,z0),(-4.,1031.,z1))
            z0,z1=sorted((side*2.8,side*3.05))
            solid('kick',(-WIDTH+4.7,1007.7,z0),(-4.7,1030.3,z1))
            for x in (-WIDTH+6.2,-6.2):
                for y in (1009.2,1028.8):
                    local['metal'].append(cylinder((x,y,side*3.2),.28,.2,axis=2,sides=8))
        for key,shapes in local.items():groups[key].extend(swing(shape,cx) for shape in shapes)
        # A slim dark surround. No opaque surface crosses the doorway.
        for x0,x1 in ((cx-70.5,cx-63.5),(cx+63.5,cx+70.5)):
            groups['frame'].append(box((x0,1000.4,1541.4),(x1,1242.5,1561.2)))
        groups['frame'].append(box((cx-70.5,1234.4,1541.4),(cx+70.5,1242.5,1561.2)))
        # Existing club-colored sign stays in its original atlas and position.
        groups['frame'].append(box((cx-66.6,1243.9,1542.6),(cx+66.6,1278.1,1545.3)))
        for y in (1027.,1119.,1211.):
            groups['metal'].append(cylinder((cx+66.,y,HINGE_Z),.85,10.))
    return groups


def fixture_mask(vertices,indices):
    p=vertices['p'][indices.reshape(-1,3)]
    mask=np.zeros(len(p),dtype=bool)
    for name,cx in DOORS:
        mask|=((p>=[cx-85,999,1530])&(p<=[cx+85,1243,1690])).all((1,2))
    return mask


def strip_old_fixtures(rx,kind):
    """Trim only retired leaves, hardware and frames, keeping wall apertures."""
    # The old pale lintel undersides also live in the room's neutral wall
    # material (slot 0), outside the retired metal and dark door batches.
    slots=(0,1,2) if kind=='interior' else (0,4,6) if kind=='roles' else ()
    if not slots:raise ValueError('Unsupported room door source')
    counts={}
    for slot in slots:
        v,idx=read_mesh(rx,slot);tri=idx.reshape(-1,3);drop=fixture_mask(v,idx)
        counts[str(slot)]=int(drop.sum())
        if not drop.any():continue
        kept=tri[~drop]
        if not len(kept):raise ValueError('Refusing to remove a whole room material')
        used,inverse=np.unique(kept,return_inverse=True)
        replace_mesh(rx,slot,v[used],inverse.reshape(-1).astype('<u2'))
    if not sum(counts.values()):raise ValueError('Existing room doors not found; do not publish')
    return counts


def obstacles(items):
    result=[]
    for item in items:
        old=False
        if item['name'].startswith('Salas / portas abertas'):
            lo=np.array(item['lo']);hi=np.array(item['hi'])
            for _,cx in DOORS:
                if (lo>=[cx-85,-1,1530]).all() and (hi<=[cx+85,243,1690]).all():old=True
        if not old:result.append(copy.deepcopy(item))
    for name,cx in DOORS:
        # Room-local Y coordinates, matching the actual open leaf and jambs.
        for part,lo,hi in [
            ('leaf',[cx+63.8,1.5,HINGE_Z],[cx+68.2,TOP-1000,HINGE_Z+WIDTH]),
            ('left jamb',[cx-70.5,.4,1541.4],[cx-63.5,242.5,1561.2]),
            ('right jamb',[cx+63.5,.4,1541.4],[cx+70.5,242.5,1561.2]),
            ('header',[cx-70.5,234.4,1541.4],[cx+70.5,242.5,1561.2])]:
            result.append(dict(name='Current Dressing Room / '+name+' door / '+part,lo=lo,hi=hi))
    return result


def specification():
    return dict(revision=1,finish_setting='door_finish',shared_with_exit=True,
                doors=[dict(id=name,center_x_cm=cx,hinge=[cx+66,1000,HINGE_Z],
                            width_cm=WIDTH,height_cm=TOP-BOTTOM,open_degrees=90) for name,cx in DOORS])
