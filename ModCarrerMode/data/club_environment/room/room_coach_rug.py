"""One thin woven office rug, independent of career/fixture image caches."""
import math
import numpy as np
from PIL import Image
from room_visual_r68 import VERT,packed

BOUNDS=(35.,485.,2020.,2430.)


def geometry():
    x0,x1,z0,z1=BOUNDS;radius=7.;ring=[]
    for x,z,start in ((x1-radius,z1-radius,0),(x0+radius,z1-radius,90),
                      (x0+radius,z0+radius,180),(x1-radius,z0+radius,270)):
        for a in np.linspace(start,start+90,9,endpoint=False):
            rad=math.radians(float(a));ring.append((x+radius*math.cos(rad),z+radius*math.sin(rad)))
    v=np.zeros(1+len(ring)*2,dtype=VERT);v['n']=packed([0,1,0]);v['g']=packed([1,0,0])
    v['p'][0]=[(x0+x1)/2,1000.96,(z0+z1)/2];v['uv'][0]=[.5,.5]
    for i,(x,z) in enumerate(ring):
        for offset,height in ((1,1000.96),(1+len(ring),1000.50)):
            v['p'][offset+i]=[x,height,z];v['uv'][offset+i]=[(x-x0)/(x1-x0),(z-z0)/(z1-z0)]
    ids=[];n=len(ring)
    for i in range(n):
        a,b=1+i,1+(i+1)%n
        ids.extend((0,b,a,a,b,b+n,a,b+n,a+n))
    return v,np.asarray(ids,dtype='<u2')


def texture(primary):
    # Same deterministic 512px textile for every match. Only the fine border
    # follows the club palette; it does not create one texture per player/date.
    y,x=np.indices((512,512));rng=np.random.default_rng(7611)
    weave=((x//2+y//2)%2)*2-1
    noise=rng.integers(-2,3,(512,512));base=np.array([52,57,61])
    rgb=np.clip(base+weave[:,:,None]*2+noise[:,:,None],0,255).astype('uint8')
    distance=np.minimum.reduce([x,511-x,y,511-y])
    rgb[distance<9]=[36,40,44]
    colour=np.asarray(primary)*.60+np.array([42,45,48])*.40
    rgb[(distance>=13)&(distance<=15)]=colour.astype('uint8')
    return Image.fromarray(rgb).convert('RGBA')
