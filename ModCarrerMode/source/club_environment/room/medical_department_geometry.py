"""Detailed clinical furniture in native centimetres, Y=1000 at the floor."""
import math
from collections import defaultdict
import numpy as np
from room_visual_r68 import VERT,box,packed
from room_interior_r71 import panel
from room_interior_r72 import lathe
from room_secondary_wall_r75 import cushion

LEFT,RIGHT,FRONT,BACK,TOP=-1550.,-335.,1555.,2890.,1338.
BOARDS={
 'injuries':([-1540.,1215.,2090.],340.,180.,(1,0,0)),
 'summary':([-345.,1215.,1810.],210.,130.,(-1,0,0)),
 'followup':([-345.,1220.,2180.],210.,125.,(-1,0,0)),
 'knee':([-1540.,1220.,2470.],92.,142.,(1,0,0)),
 'spine':([-1540.,1220.,2680.],92.,142.,(1,0,0)),
 'identity':([-1200.,1234.,BACK-.6],580.,150.,(0,0,-1))}
SCENES={
 'entrada':[-630,180,1705,-1090,150,2290,76],
 'atendimento':[-950,175,1630,-1210,117,1750,68],
 'situação do elenco':[-1110,195,2120,-1540,215,2090,56],
 'tratamento':[-1030,180,2400,-1355,100,2305,67],
 'anatomia':[-1100,210,2560,-1540,220,2560,60],
 'reabilitação':[-1070,180,2440,-650,135,2490,76],
 'recuperação':[-1040,200,2720,-810,135,2790,70]}


class Scene:
 def __init__(self):self.groups=defaultdict(list);self.obstacles=[]
 def add(self,material,shape):self.groups[material].append(shape)
 def box(self,material,lo,hi):self.add(material,box(lo,hi))
 def collision(self,name,lo,hi):self.obstacles.append(dict(name='Medical department / '+name,lo=[lo[0],lo[1]-1000,lo[2]],hi=[hi[0],hi[1]-1000,hi[2]]))
 def tube(self,material,a,b,r,sides=16):
  a,b=np.array(a,float),np.array(b,float);n=b-a;length=np.linalg.norm(n)
  if length<1e-6:return
  n/=length;u=np.cross(n,[1,0,0] if abs(n[0])<.8 else [0,0,1]);u/=np.linalg.norm(u);w=np.cross(n,u)
  vertices=[];indices=[]
  for center in (a,b):
   for i in range(sides+1):
    normal=u*math.cos(i*math.tau/sides)+w*math.sin(i*math.tau/sides);vertices.append((center+normal*r,packed(normal),packed(n),(i/sides,0)))
  for i in range(sides):j=i+sides+1;indices.extend((i,i+1,j+1,i,j+1,j))
  for center,normal in ((a,-n),(b,n)):
   start=len(vertices);vertices.append((center,packed(normal),packed(u),(.5,.5)))
   for i in range(sides+1):vertices.append((center+(u*math.cos(i*math.tau/sides)+w*math.sin(i*math.tau/sides))*r,packed(normal),packed(u),(.5,.5)))
   for i in range(sides):indices.extend((start,start+i+1,start+i+2))
  v=np.zeros(len(vertices),dtype=VERT)
  for i,row in enumerate(vertices):v[i]=row
  self.add(material,(v,np.asarray(indices,dtype='<u2')))
 def wheel(self,x,y,z,r=3.5):
  self.tube('rubber',(x-1.8,y,z),(x+1.8,y,z),r,20);self.tube('metal',(x-2.2,y,z),(x+2.2,y,z),r*.35,12)
 def pad(self,lo,hi):self.add('padding',cushion(lo,hi))
 def framed(self,key):
  center,width,height,normal=BOARDS[key];c=np.array(center,float);n=np.array(normal,float)
  self.add('frame',panel(c,width+3,height+3,normal));self.add('board_'+key,panel(c+n*.25,width,height,normal))


def clinical():
 s=Scene();b=s.box;t=s.tube
 walls=[((LEFT-10,1000,FRONT),(LEFT,TOP,BACK+10)),((RIGHT,1000,FRONT),(RIGHT+10,TOP,BACK+10)),((LEFT-10,1000,BACK),(RIGHT+10,TOP,BACK+10)),
        ((LEFT,1000,1544.3),(-615,TOP,1555)),((-475,1000,1544.3),(RIGHT,TOP,1555)),((-615,1240,1544.3),(-475,TOP,1555))]
 for lo,hi in walls:b('white',lo,hi);s.collision('wall',lo,hi)
 b('floor',(LEFT,995,FRONT),(RIGHT,1000.3,BACK));b('ceiling',(LEFT,TOP,FRONT),(RIGHT,TOP+6,BACK))
 for x in (LEFT+.4,RIGHT-.4):b('trim',(x-1,1000.5,FRONT),(x+1,1008,BACK))
 b('trim',(LEFT,1000.5,BACK-1),(RIGHT,1008,BACK))
 # Long recessed ceiling lights; no painted illumination or dirty lightmaps.
 for x in (-1360,-980,-600):
  for z in (1770,2190,2610):
   b('metal',(x-3,TOP-2,z-100),(x+3,TOP-.4,z+100));b('light',(x-2.3,TOP-2.2,z-99),(x+2.3,TOP-2,z+99))
 for x in (-1480,-400):
  for z in (1830,2400,2800):
   b('trim',(x-20,TOP-1,z-15),(x+20,TOP,z+15))
   for k in range(8):b('white',(x-18,TOP-1.2,z-13+k*3.5),(x+18,TOP-1,z-12+k*3.5))
 # Neutral consultation rug. Imported desk, notebook, telephone and cup sit here.
 b('rug',(-1390,1000.35,1575),(-1045,1000.8,1885))
 s.collision('consultation desk',(-1335,1000,1680),(-1085,1112,1782))
 s.collision('doctor chair',(-1258,1000,1787),(-1160,1120,1848))
 s.collision('visitor chairs',(-1338,1000,1584),(-1084,1104,1656))
 # White clinical storage: inset doors, hinges, pulls, clean worktop and sink.
 b('white',(LEFT+4,1001,1880),(LEFT+63,1085,2770));b('worktop',(LEFT+2,1085,1878),(LEFT+66,1089,2772))
 for z in range(1883,2760,74):
  b('cabinet',(LEFT+63.2,1007,z),(LEFT+65,1081,min(z+70,2767)));b('metal',(LEFT+65.2,1061,z+22),(LEFT+67,1063,z+48))
 s.collision('clinical storage',(LEFT,1000,1880),(LEFT+67,1089,2772))
 # Stainless sink at the far end, tap and soap dispenser.
 b('metal',(LEFT+9,1089.2,2700),(LEFT+58,1090,2752));b('sink',(LEFT+13,1089.4,2705),(LEFT+54,1089.6,2747))
 t('metal',(LEFT+17,1090,2730),(LEFT+17,1116,2730),1.6)
 t('metal',(LEFT+17,1116,2730),(LEFT+43,1116,2730),1.6);t('metal',(LEFT+43,1116,2730),(LEFT+43,1110,2730),1.6)
 for z in (2670,2645):
  b('white',(LEFT+21,1089,z),(LEFT+37,1110,z+13));t('metal',(LEFT+29,1110,z+6),(LEFT+29,1114,z+6),1)
 for k in range(7):b('linen',(LEFT+10,1089+k*2.6,2590),(LEFT+55,1091+k*2.6,2622))
 # Articulated three-section treatment tables with lifting mechanism and casters.
 for z in (1985.,2305.,2625.):
  x=-1355.;b('metal',(x-110,1068,z-38),(x+112,1074,z+38));s.pad((x-45,1075,z-37),(x+110,1086,z+37))
  head,idx=cushion((-36,-4,-37),(36,4,37));head=head.copy();a=-.42;r=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
  head['p']=head['p']@r.T+[x-78,1094,z]
  for field in ('n','g'):
   raw=head[field].astype(np.int64);n=np.column_stack([(raw>>(10*i))&1023 for i in range(3)]);n=np.where(n>=512,n-1024,n)/511;head[field]=[packed(v) for v in n@r.T]
  s.add('padding',(head,idx));b('frame',(x-109,1064,z-36),(x-46,1068,z+36))
  for dz in (-29,29):
   t('metal',(x-88,1014,z+dz),(x+80,1068,z+dz),2.4);t('metal',(x-88,1068,z+dz),(x+80,1014,z+dz),2.4)
   t('metal',(x-98,1012,z+dz),(x+96,1012,z+dz),2.5)
   for dx in (-92,90):s.wheel(x+dx,1004.3,z+dz,4.1)
  t('metal',(x,1016,z),(x,1067,z),4.2);t('trim',(x,1020,z),(x+48,1057,z),2.2)
  t('rubber',(x-54,1009,z-45),(x-20,1009,z-45),1.4)
  for k in range(3):b('linen',(x+47,1086.2+k*2.3,z-22),(x+89,1088.2+k*2.3,z+22))
  s.collision('treatment table',(x-114,1000,z-41),(x+114,1120,z+41))
  # Wheeled treatment cart with shelves, console, controls and flexible cable.
  cx,cz=-1163.,z+76
  for y in (1010,1044,1082):b('white',(cx-26,y,cz-21),(cx+26,y+2.5,cz+21))
  for dx in (-23,23):
   for dz in (-18,18):t('metal',(cx+dx,1004,cz+dz),(cx+dx,1090,cz+dz),1.2);s.wheel(cx+dx,1003,cz+dz,2.7)
  b('cabinet',(cx-21,1085,cz-17),(cx+21,1105,cz+17));b('screen',(cx-15,1105.1,cz-12),(cx+15,1105.3,cz+5))
  for dx in (-13,0,13):t('metal',(cx+dx,1094,cz-18),(cx+dx,1094,cz-19),2.1,12)
  curve=[[cx-25-48*t,1087-24*math.sin(t*math.pi),cz-8+20*t] for t in np.linspace(0,1,15)]
  for a,c in zip(curve,curve[1:]):t('rubber',a,c,.55,8)
  s.collision('treatment trolley',(cx-28,1000,cz-23),(cx+28,1110,cz+23))
  sx,sz=-1150.,z-70;s.add('padding',lathe([sx,1050,sz],[(0,0),(0,18),(6,18),(8,16),(8,0)],24))
  t('metal',(sx,1007,sz),(sx,1050,sz),2.4)
  for a in np.linspace(0,math.tau,5,endpoint=False):
   end=[sx+22*math.cos(a),1005,sz+22*math.sin(a)];t('metal',(sx,1008,sz),end,1.4);s.wheel(end[0],1003,end[2],2.5)
  s.collision('clinician stool',(sx-24,1000,sz-24),(sx+24,1060,sz+24))
 for key in BOARDS:s.framed(key)
 # Exactly one printed plaque per door, on the unchanged fitted supports.
 for kind,x in (('medical',-545),('coach',180)):
  s.add('board_door_'+kind,panel([x,1261,1542.2],132,33,(0,0,-1)))
 return s


def treadmill():
 s=Scene();b=s.box;t=s.tube
 # Local floor = 0, forward = +Z; two instances share these native buffers.
 b('frame',(-57,8,-120),(57,19,120));b('belt',(-45,19.2,-104),(45,20.1,85))
 for x in (-53,53):
  b('metal',(x-5,19,-110),(x+5,22,93));t('metal',(x,11,76),(x,120,85),4,20)
  for z in (-96,92):s.wheel(x,5,z,5)
  t('rubber',(x,121,83),(x,118,15),2.3,20)
 t('metal',(-56,117,86),(56,117,86),3.5,20)
 b('frame',(-53,118,77),(53,128,102));b('screen',(-31,128.1,80),(31,128.4,98))
 for x in (-40,40):t('trim',(x,128.5,91),(x,129,91),3.8,20)
 t('safety',(-4,129,79),(4,129,79),2.4,16)
 for x in (-54,54):b('trim',(x-1,21,-100),(x+1,21.3,65))
 for z in (-103,84):t('rubber',(-46,18.2,z),(46,18.2,z),3.4,20)
 return s


def bicycle():
 s=Scene();b=s.box;t=s.tube
 for z in (-49,51):t('metal',(-34,6,z),(34,6,z),3.5,20)
 for z in (-49,51):
  for x in (-34,34):t('rubber',(x-3,6,z),(x+3,6,z),4.2,16)
 t('metal',(0,9,-47),(0,53,-8),5,20);t('metal',(0,53,-8),(0,15,48),5,20)
 t('metal',(0,15,48),(0,102,39),3.3,20);t('metal',(0,50,-6),(0,91,-30),3,20)
 b('frame',(-9,18,-18),(9,44,40));t('trim',(-10,39,17),(10,39,17),23,40)
 t('frame',(-10.3,39,17),(10.3,39,17),16,32);t('metal',(-13,35,-5),(13,35,-5),2.3,16)
 for side in (-1,1):
  t('metal',(side*13,35,-5),(side*14,35+side*12,-5+side*15),1.7)
  b('rubber',(side*15-5,33+side*12,-12+side*15),(side*15+5,37+side*12,4+side*15))
 s.add('padding',cushion((-16,91,-43),(16,97,-19)))
 for side in (-1,1):
  t('metal',(0,102,39),(side*25,102,39),2.1);t('rubber',(side*25,102,39),(side*25,111,17),2.4,20)
 b('screen',(-10,111,25),(10,114,40));t('trim',(0,100,39),(0,112,33),1.5)
 t('metal',(13,55,4),(13,64,4),1.3);t('safety',(10,64,4),(16,64,4),2,16)
 return s


def rehabilitation():
 s=Scene();b=s.box;t=s.tube
 # Compact dual-pulley station, with individual plates, guide rails and grips.
 x,z=-800.,2820.
 for dx in (-78,78):
  b('frame',(x+dx-4,1003,z-38),(x+dx+4,1250,z+23))
  b('rubber',(x+dx-10,1000.5,z-44),(x+dx+10,1004,z+29))
  for dz in (-8,8):t('metal',(x+dx,1008,z+dz),(x+dx,1236,z+dz),1.2,16)
  for y in range(1014,1110,8):b('rubber',(x+dx-23,y,z-17),(x+dx+23,y+6,z+17))
  for y in (1116,1218):t('metal',(x+dx-2,y,z-17),(x+dx+2,y,z-17),6.2,24)
  t('rubber',(x+dx,1116,z-23),(x+dx,1220,z-23),.5,8)
  t('rubber',(x+dx,1220,z-23),(x+dx,1160,z-65),.5,8)
  for hand in (-1,1):t('metal',(x+dx,1160,z-65),(x+dx+hand*11,1148,z-65),.9,12)
  t('rubber',(x+dx-11,1148,z-65),(x+dx+11,1148,z-65),1.5,16)
  b('trim',(x+dx-1,1079,z-25),(x+dx+1,1082,z-18))
 b('frame',(x-80,1246,z-24),(x+80,1253,z+23))
 s.collision('dual-pulley station',(x-110,1000,z-85),(x+110,1255,z+32))
 # Wall ladder: rounded wooden rungs with visible mounting brackets.
 for zz in (2630,2730):
  b('wood',(-359,1004,zz-3),(-349,1265,zz+3))
  for y in (1020,1130,1240):b('metal',(-355,y,zz-5),(-335,y+6,zz+5))
 for y in range(1020,1250,20):t('wood',(-361,y,2630),(-361,y,2730),1.8,20)
 s.collision('wall ladder',(-365,1000,2623),(-335,1268,2737))
 # Non-slip exercise mats, foam rollers, stability balls and balance pad.
 for cx in (-950,-600):
  b('rug',(cx-36,1000.4,2673),(cx+36,1001,2833))
 b('white',(-1500,1001,2825),(-1190,1075,2880));b('worktop',(-1502,1075,2823),(-1188,1077,2882))
 s.collision('rehabilitation storage',(-1502,1000,2815),(-1188,1143,2882))
 for cx,radius in ((-1460,32),(-1370,27)):
  profile=[(radius*(1-math.cos(a)),radius*math.sin(a)) for a in np.linspace(0,math.pi,22)]
  s.add('padding',lathe([cx,1077,2850],profile,28))
 for cx in (-1290,-1267,-1244):
  t('padding',(cx,1077,2860),(cx,1118,2860),8,20)
  for y in (1086,1100,1114):t('trim',(cx,y,2860),(cx,y+.5,2860),8.2,20)
 return s
