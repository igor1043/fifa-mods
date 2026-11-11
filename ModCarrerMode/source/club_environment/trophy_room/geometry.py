"""One reusable museum shell; competition cups are always installed FIFA meshes.

Coordinates are centimetres, Y up. Display slots belong to the two side walls.
The editable identity wall is a separate surface, never baked into the shell.
"""
import math
from collections import defaultdict
import numpy as np

WIDTH, DEPTH, HEIGHT = 1300., 1500., 330.
CAPACITY = 30
REVISION = 6
IDENTITY_SIZE = (1920, 640)
IDENTITY_WIDTH, IDENTITY_HEIGHT = 960., 320.


def slots():
    return [dict(index=i, side='left' if i < 15 else 'right',
                 x=-565. if i < 15 else 565., y=102., z=-630.+(i % 15)*90.,
                 yaw=math.pi/2 if i < 15 else -math.pi/2,
                 plaque_x=-494. if i < 15 else 494.) for i in range(CAPACITY)]


class Scene:
    def __init__(self):
        self.parts = []
        self.obstacles = []

    def mesh(self, name, material, positions, indices, uvs=None):
        self.parts.append(dict(name=name, material=material, positions=positions,
                               indices=indices, uvs=uvs or []))

    def box(self, name, material, center, size, collision=False):
        lo=np.asarray(center)-np.asarray(size)/2;hi=np.asarray(center)+np.asarray(size)/2
        points=[];uv=[];ids=[]
        for axis in range(3):
            a,b=(axis+1)%3,(axis+2)%3
            for side in (0,1):
                start=len(points)
                for u,v in ((0,0),(1,0),(1,1),(0,1)):
                    p=lo.copy();p[axis]=hi[axis] if side else lo[axis]
                    p[a]=hi[a] if u else lo[a];p[b]=hi[b] if v else lo[b]
                    points.append(p.tolist());uv.append([u,1-v])
                ids.extend(start+k for k in ([0,1,2,0,2,3] if side else [0,2,1,0,3,2]))
        self.mesh(name,material,points,ids,uv)
        if collision:self.obstacles.append(dict(lo=lo.tolist(),hi=hi.tolist()))

    def panel(self,name,material,center,width,height,yaw=0):
        c,s=math.cos(yaw),math.sin(yaw);points=[]
        for x,y in ((-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)):
            points.append([center[0]+x*c,center[1]+y,center[2]-x*s])
        self.mesh(name,material,points,[0,1,2,0,2,3],[[0,1],[1,1],[1,0],[0,0]])


def build():
    from . import furnishings
    s=Scene()
    s.box('Floor','stone',(0,-5,0),(WIDTH+30,10,1530))
    s.box('Ceiling','ceiling',(0,337,0),(WIDTH+30,14,1530))
    s.box('Left wall','wall',(-WIDTH/2-10,165,0),(20,330,1530))
    s.box('Right wall','wall',(WIDTH/2+10,165,0),(20,330,1530))
    s.box('Identity wall','wall',(0,165,-760),(WIDTH,330,20))
    s.box('Entrance wall','wall',(0,165,760),(WIDTH,330,20))
    for x in (-WIDTH/2+2,WIDTH/2-2):
        s.box('Skirting','aluminium',(x,7,0),(4,14,1500))
    s.box('Entrance skirting','aluminium',(0,7,748),(WIDTH-4,14,4))
    # Keep the skirting away from the editable image. The previous front face
    # was coplanar with the mural and cut through its lower edge.
    end=(WIDTH-4)/2;start=IDENTITY_WIDTH/2+2
    for side in (-1,1):
        s.box('Identity side skirting','aluminium',(side*(start+end)/2,7,-748),(end-start,14,4))
    # A closed door belongs to the room, never a passage to another scene.
    furnishings.exit_door(s)
    s.panel('Club identity','identity',(0,165,-746),IDENTITY_WIDTH,IDENTITY_HEIGHT)
    # Both long vitrines use exactly the same module and spacing.
    for side in (-1,1):
        x=side*572
        s.box('Cabinet lower body','cabinet',(x,39,0),(148,78,1400),True)
        s.box('Cabinet top','cabinet',(x,278,0),(148,15,1400))
        s.box('Cabinet inner back','case_back',(side*644,174,0),(4,182,1394))
        s.box('Lower display shelf','shelf',(x,80,0),(148,5,1400))
        s.box('Cabinet lower reveal','secondary',(side*498,77,0),(2,2,1400))
        s.box('Cabinet upper reveal','primary',(side*498,274,0),(2,2,1400))
        s.box('Cabinet lamp','emission',(x,267,0),(126,2,1384))
        for z in (-701,701):s.box('Cabinet end','aluminium',(x,175,z),(150,190,3))
        for z in (-700,-350,0,350,700):
            s.box('Glass seam','aluminium',(side*497,175,z),(2,189,1.4))
        for z in (-525,-175,175,525):
            s.box('Clear display glass','glass',(side*495,176,z),(0.6,183,347))
    for slot in slots():
        i=slot['index'];x,z=slot['x'],slot['z']
        s.box(f'Pedestal {i+1}','plinth',(x,92,z),(108,22,82))
        # A very narrow reveal makes the plinth a fitted display component.
        s.box(f'Pedestal foot {i+1}','aluminium',(x,81,z),(105,2,79))
        s.panel(f'Plaque {i+1}','plaque_'+str(i),
                (slot['plaque_x'],93,z),78,17,slot['yaw'])
    furnishings.bench(s)
    for x in (-470,470):
        s.box('Ceiling track','black',(x,325,0),(4,4,1390))
        for z in (-575,-287,0,287,575):
            s.box('Spotlight housing','black',(x,312,z),(10,21,10))
            s.box('Spotlight lens','emission',(x,300.5,z),(8,1,8))
    for x in (-170,170):s.box('Ceiling linear light','emission',(x,329,0),(3,1,1300))
    # Flush ceiling seams, rather than high contrast 3D grid lines.
    for z in range(-720,721,120):s.box('Ceiling panel joint','joint',(0,329.7,z),(WIDTH-5,.2,.3))
    return dict(revision=REVISION,dimensions=[WIDTH,HEIGHT,DEPTH],capacity=CAPACITY,
                parts=s.parts,slots=slots(),obstacles=s.obstacles,
                cameras=[dict(eye=[0,166,660],target=[0,155,-380],fov=70),
                         dict(eye=[365,166,520],target=[-560,156,-70],fov=65),
                         dict(eye=[-365,166,520],target=[560,156,-70],fov=65),
                         dict(eye=[0,170,-310],target=[0,165,-744],fov=84)])


MATERIALS=dict(stone=('#b5b8b8',.60,0),wall=('#e4e6e4',.76,0),ceiling=('#f0f0eb',.8,0),
               aluminium=('#8a9497',.27,.76),cabinet=('#c3c8c7',.53,.1),
               case_back=('#c4c8c3',.7,0),shelf=('#eeeae0',.38,.1),plinth=('#e8e6df',.47,0),
               bench=('#333639',.48,.1),leather=('#393b3c',.61,0),door=('#c7cbd0',.48,.25),
               chrome=('#ccd0d2',.16,.92),black=('#171a1c',.42,.2),joint=('#d7d9d6',.8,0),
               primary=('#bd1528',.43,.25),secondary=('#202020',.48,.15),
               emission=('#fff6df',.3,0),glass=('#dce8e5',.06,0))
