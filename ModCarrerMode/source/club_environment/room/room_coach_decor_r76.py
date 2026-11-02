"""Office dressing: physical books, trophy, plants, clock and club keepsakes."""
import math
import numpy as np
from room_visual_r68 import VERT,box,packed
from room_interior_r71 import panel
from room_interior_r72 import lathe

# Flat product colors share an unused strip of the existing panel atlas.
SWATCHES=[(37,91,64),(56,122,74),(98,146,79),(105,74,49),(235,231,216),
          (36,63,96),(145,45,50),(189,151,74),(150,162,169),(26,29,32),
          (227,233,234),(89,67,49),(41,86,109),(170,127,64),(94,101,111),(205,199,185)]


def decorate(add,solid,region):
    def paint(shape,index):
        v,ids=shape;v=v.copy();v['uv'][:]=((2048+index*128+64)/4096,(4032+32)/4096);return v,ids
    def colored(shape,index):add('panels',paint(shape,index))
    def tube(a,b,r,index,sides=10):
        a,b=np.array(a,float),np.array(b,float);direction=b-a;direction/=np.linalg.norm(direction)
        u=np.cross(direction,[1,0,0] if abs(direction[0])<.8 else [0,0,1]);u/=np.linalg.norm(u);w=np.cross(direction,u)
        v=np.zeros((sides+1)*2,dtype=VERT);ids=[]
        for j,center in enumerate((a,b)):
            for k in range(sides+1):
                n=u*math.cos(k*math.tau/sides)+w*math.sin(k*math.tau/sides);v[j*(sides+1)+k]=(center+n*r,packed(n),packed(u),(.5,.5))
        for k in range(sides):a0=k;b0=k+sides+1;ids.extend([a0,a0+1,b0+1,a0,b0+1,b0])
        colored((v,np.array(ids,dtype='<u2')),index)

    # Archive wall: open shelves, individually sized books and ring binders.
    add('primary',box((350,1001,1563),(715,1183,1568)))
    for x in (350,440,530,620,710):add('dark',box((x,1000.5,1566),(x+5,1184,1611)))
    for y in (1004,1045,1090,1180):add('dark',box((350,y,1566),(715,y+4,1612)))
    for a,b in ((350,530),(620,715)):add('dark',box((a,1135,1566),(b,1139,1612)))
    for row,y in enumerate((1009,1050,1095,1140)):
        for column,a in enumerate((360,450,630)):
            for j in range(7 if (row+column)%2 else 5):
                x=a+j*9;h=22+(j*7+row*3)%13;index=(5,6,12,9,13,14,4)[(j+row+column)%7]
                colored(box((x,y,1571),(x+7,y+h,1606)),index)
                colored(box((x+1,y+h-8,1606.1),(x+6,y+h-3,1606.3)),10)
                colored(box((x+2,y+4,1606.2),(x+5,y+7,1606.4)),8)
    solid('estante de arquivos',(350,1000.5,1563),(715,1184,1612))
    # A reusable sculpted cup, with stem, bowl, two curved handles and a plinth.
    colored(box((548,1094,1577),(602,1100,1610)),9)
    profile=[(0,0),(0,19),(4,19),(6,6),(18,4),(21,6),(24,14),(33,21),(43,24),(45,23),(45,0)]
    colored(lathe([575,1100,1591],profile,40),7)
    for side in (-1,1):
        pts=[[575+side*(18+16*math.sin(t*math.pi)),1138-t*28,1591] for t in np.linspace(0,1,14)]
        for a,b in zip(pts,pts[1:]):tube(a,b,1.8,7)
    # Framed real kit, club mural and a conventional analog clock.
    add('dark',box((-120,1076,1562),(0,1214,1566)))
    add('panels',panel([-60,1145,1566.2],112,130,(0,0,1),region(6,(0,512,512,1024))))
    add('dark',box((396,1200,1562),(674,1298,1566)))
    add('panels',panel([535,1249,1566.2],270,90,(0,0,1),region(6,(1024,512,2048,853.3333))))
    v,ids=lathe([0,0,0],[(0,0),(0,35),(4,35),(4,0)],48)
    p=v['p'].copy();n=v['n'].copy();v['p'][:,0]=p[:,0]-230;v['p'][:,1]=1245-p[:,2];v['p'][:,2]=1562+p[:,1]
    add('metal',(v,ids));add('panels',panel([-230,1245,1566.2],66,66,(0,0,1),region(6,(512,512,1024,1024))))

    # Two plants with curved, double-sided leaf blades and separate stems.
    for x,z in ((-225,1670),(670,2420)):
        colored(lathe([x,1000.5,z],[(0,0),(0,18),(3,20),(38,26),(43,26),(43,22),(44,0)],40),9)
        colored(lathe([x,1044.6,z],[(0,0),(0,22),(.8,22),(.8,0)],32),3)
        for leaf in range(10):
            angle=leaf*2.39996;reach=40+(leaf%3)*11;height=75+(leaf%4)*12
            start=np.array([x,1045,z],float);end=start+[math.cos(angle)*reach,height,math.sin(angle)*reach]
            tube(start,start+(end-start)*.64,.7,0,7)
            rows=[];indices=[];side=np.array([-math.sin(angle),0,math.cos(angle)])
            for step in range(8):
                t=step/7;center=start+np.array([math.cos(angle)*reach*t,height*math.sin(t*math.pi*.6),math.sin(angle)*reach*t]);width=math.sin(math.pi*t)*8
                rows.extend([center-side*width,center+[0,2,0],center+side*width])
            triangles=[]
            for s in range(7):
                for k in range(2):a=s*3+k;b=a+3;triangles.extend([(a,a+1,b+1),(a,b+1,b)])
            vv=np.zeros(len(triangles)*6,dtype=VERT);cursor=0
            for tri in triangles:
                points=np.array([rows[i] for i in tri]);normal=np.cross(points[1]-points[0],points[2]-points[0]);size=np.linalg.norm(normal)
                if size<.00001:continue
                normal/=size
                for order,sign in (([0,1,2],1),([2,1,0],-1)):
                    for i in order:vv[cursor]=(points[i],packed(normal*sign),packed(side),(.5,.5));cursor+=1
            colored((vv[:cursor],np.arange(cursor,dtype='<u2')),leaf%3)
        solid('vaso',(x-26,1000,z-26),(x+26,1045,z+26))

    # Desk details: keyboard, mouse, coffee mug, pen cup and a simple task lamp.
    for row in range(5):
        for key in range(10):colored(box((115+key*5.4,1088.6,2111+row*4.6),(119+key*5.4,1089.1,2114+row*4.6)),14)
    colored(lathe([184,1086.2,2132],[(0,0),(0,4),(1,5),(3.5,4),(4.5,0)],24),9)
    colored(lathe([60,1086.2,2148],[(0,0),(0,4.5),(11,4.8),(12,4.8),(12,0)],28),10)
    colored(lathe([60,1098.4,2148],[(0,0),(0,4),(.2,4),(.2,0)],28),11)
    pts=[[65+3*math.sin(t*math.pi),1096-9*t,2148] for t in np.linspace(0,1,12)]
    for a,b in zip(pts,pts[1:]):tube(a,b,.9,10)
    colored(lathe([301,1086.2,2089],[(0,0),(0,4),(11,4),(11,0)],24),9)
    for j in range(5):tube([298+j*1.2,1087,2089],[298+j*1.8,1111+j%2*2,2089],.45,5+j%2,6)
    add('metal',lathe([60,1086,2086],[(0,0),(0,7),(1.5,7),(2.5,5),(2.5,0)],28))
    tube([60,1088,2086],[60,1121,2086],1.2,8);tube([60,1121,2086],[74,1126,2095],1.2,8)
    add('dark',box((64,1123,2090),(88,1128,2104)));add('light',box((66,1122.8,2092),(86,1123,2102)))
    add('dark',box((285,1086.5,2107),(314,1107,2109)));add('panels',panel([299.5,1097,2109.2],26,17,(0,0,1),region(6,(1024,512,2048,853.3333))))
