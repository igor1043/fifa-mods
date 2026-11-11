"""Museum furniture and the same closed safety door used by the dressing room."""
from pathlib import Path
import math
import sys
import numpy as np


def cushion(scene, name, center, width, length, height, radius=3.5):
    """Rounded upholstery with real edge geometry, not a painted highlight."""
    cx,cy,cz=center;points=[];uvs=[];indices=[]
    def outline(inset):
        w,l=width/2-inset,length/2-inset;r=max(.5,radius-inset)
        return [(cx+x0+r*math.cos(a),cz+z0+r*math.sin(a))
                for x0,z0,start in ((w-r,l-r,0),(-w+r,l-r,90),(-w+r,-l+r,180),(w-r,-l+r,270))
                for a in (math.radians(start+k*90/5) for k in range(6))]
    bevel=1.2;n=24;stride=n+1
    border=outline(0);distance=[0.]
    for i in range(n):distance.append(distance[-1]+math.dist(border[i],border[(i+1)%n]))
    for y,inset in ((cy-height/2,bevel),(cy-height/2+bevel,0),
                    (cy+height/2-bevel,0),(cy+height/2,bevel)):
        ring=outline(inset)
        for i,(x,z) in enumerate(ring+[ring[0]]):
            points.append([x,y,z]);uvs.append([distance[i]/width,(y-cy+height/2)/width])
    for ring in range(3):
        for i in range(n):
            a=ring*stride+i;b=a+1;c=b+stride;d=a+stride
            indices.extend((a,c,b,a,d,c))
    for ring,up in ((0,False),(3,True)):
        start=len(points);points.append([cx,cy+height/2 if up else cy-height/2,cz]);uvs.append([.5,.5])
        for x,z in outline(bevel):
            points.append([x,cy+height/2 if up else cy-height/2,z])
            uvs.append([(x-cx)/width+.5,(z-cz)/length+.5])
        for i in range(n):
            a=start+1+i;b=start+1+(i+1)%n
            indices.extend((start,b,a) if up else (start,a,b))
    scene.mesh(name,'leather',points,indices,uvs)


def bench(scene):
    # Recessed supports, slim frame and six individually upholstered cushions.
    scene.box('Museum bench base','bench',(0,31,180),(80,24,338))
    scene.box('Bench seat frame','black',(0,44,180),(88,4,344))
    for z in (53,307):
        scene.box('Bench sled foot','aluminium',(0,3.5,z),(76,5,5))
        for x in (-33,33):scene.box('Bench support','black',(x,12,z),(5,14,5))
    for x in (-40.2,40.2):scene.box('Bench club inlay','primary',(x,35,180),(.5,1.2,330))
    for i in range(6):cushion(scene,f'Bench cushion {i+1}',(0,51,38.5+56.6*i),88,55.4,12)
    scene.obstacles.append(dict(lo=[-44,0,9],hi=[44,57,351]))


def exit_door(scene):
    room=Path(__file__).resolve().parents[1]/'room'
    if str(room) not in sys.path:sys.path.insert(0,str(room))
    from room_door_shapes import geometry,CENTER_Z
    materials={'leaves':'door','frame':'black','metal':'aluminium','kick':'bench'}
    for key,meshes in geometry(include_annex=False).items():
        for i,(vertices,indices) in enumerate(meshes):
            original=np.asarray(vertices['p'],dtype=float)
            # Rigid 90-degree rotation: the hardware faces into this room.
            positions=np.column_stack((260+original[:,2]-CENTER_Z,original[:,1]-1000,
                                       747-(original[:,0]+849)))
            name='Closed exit door' if key=='leaves' and i==0 else f'Exit door {key} {i+1}'
            scene.mesh(name,materials[key],positions.tolist(),indices.astype(int).tolist(),
                       np.asarray(vertices['uv'],dtype=float).tolist())
    scene.panel('Exit sign','exit',(260,262,738.5),146,27,math.pi)
