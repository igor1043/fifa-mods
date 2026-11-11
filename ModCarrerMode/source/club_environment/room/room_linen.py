"""Shared cotton material and a small, softly folded towel for each locker."""
import math
import numpy as np
from PIL import Image,ImageDraw
from room_visual_r68 import VERT,packed


def wave(x,z):
    return .06*math.sin(x*.43)*math.cos(z*.31)


def vertex(position,normal,uv):
    p=np.asarray(position,dtype=float).copy();n=np.asarray(normal,dtype=float).copy()
    x,z=p[0],p[2]
    p[1]+=wave(x,z)
    dx=.06*.43*math.cos(x*.43)*math.cos(z*.31)
    dz=-.06*.31*math.sin(x*.43)*math.sin(z*.31)
    n=np.array([n[0]-dx*n[1],n[1],n[2]-dz*n[1]])
    n/=max(1e-9,np.linalg.norm(n))
    tangent=np.array([0.,0.,1.]) if abs(n[0])>.9 else np.array([1.,0.,0.])
    tangent-=n*np.dot(tangent,n);tangent/=max(1e-9,np.linalg.norm(tangent))
    return p,packed(n),packed(tangent),uv


def rounded_fold(lo,hi,radius=.85):
    """Rounded edges with smooth normals; no rigid, sharp white blocks."""
    lo,hi=np.array(lo,dtype=float),np.array(hi,dtype=float)
    center=(lo+hi)*.5;half=(hi-lo)*.5;inner=half-radius
    if np.min(inner)<=0:raise ValueError('Fold bevel exceeds its thickness')
    axes=[]
    for h,i in zip(half,inner):
        axes.append([-h,-i-radius*.41421356,-i,0.,i,i+radius*.41421356,h])
    rows=[];indices=[]
    for axis in range(3):
        a,b=(axis+1)%3,(axis+2)%3
        for sign in (-1,1):
            start=len(rows)
            for u in axes[a]:
                for v in axes[b]:
                    q=np.zeros(3);q[axis]=sign*half[axis];q[a]=u;q[b]=v
                    anchor=np.clip(q,-inner,inner);normal=q-anchor;normal/=np.linalg.norm(normal)
                    p=center+anchor+radius*normal
                    uv=(p[0]/16,p[2]/16) if axis==1 else (p[2 if axis==0 else 0]/16,p[1]/16)
                    rows.append(vertex(p,normal,uv))
            for u in range(6):
                for v in range(6):
                    i=start+u*7+v
                    for tri in ([i,i+7,i+8],[i,i+8,i+1]):
                        points=np.array([rows[k][0] for k in tri])
                        n=np.array([0.,0.,0.]);n[axis]=sign
                        if np.dot(np.cross(points[1]-points[0],points[2]-points[0]),n)<0:tri=tri[::-1]
                        indices.extend(tri)
    vertices=np.zeros(len(rows),dtype=VERT)
    for i,row in enumerate(rows):vertices[i]=row
    return vertices,np.array(indices,dtype='<u2')


def folded_towel():
    """Coordinates are final locker-local cm, resting just above the seat."""
    body=[rounded_fold((-32,55.25,49),(-4,57.65,75.4)),
          rounded_fold((-31.6,57.9,49.2),(-3.6,60.25,75))]
    rows=[];indices=[];x0,x1=-30.6,-4.6;z0,z1=72.8,73.55
    for i in range(9):
        x=x0+(x1-x0)*i/8
        for v in (0.,1.):
            z=z0+(z1-z0)*v
            height,normal=top_surface(body[1],x,z)
            position=np.array([x,height,z])+normal*.045
            tangent=np.array([1.,0.,0.]);tangent-=normal*np.dot(tangent,normal);tangent/=np.linalg.norm(tangent)
            rows.append((position,packed(normal),packed(tangent),((x-x0)/3,v)))
    for i in range(8):
        a=i*2;indices.extend((a,a+1,a+3,a,a+3,a+2))
    vertices=np.zeros(len(rows),dtype=VERT)
    for i,row in enumerate(rows):vertices[i]=row
    return body,[(vertices,np.array(indices,dtype='<u2'))]


def top_surface(mesh,x,z):
    vertices,indices=mesh;p=vertices['p'][indices.reshape(-1,3)].astype(float)
    a,b,c=p[:,0],p[:,1],p[:,2]
    den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2])
    good=(np.abs(den)>1e-8)&(p[:,:,1].min(1)>59)
    wa=np.divide((b[:,2]-c[:,2])*(x-c[:,0])+(c[:,0]-b[:,0])*(z-c[:,2]),den,out=np.zeros(len(p)),where=good)
    wb=np.divide((c[:,2]-a[:,2])*(x-c[:,0])+(a[:,0]-c[:,0])*(z-c[:,2]),den,out=np.zeros(len(p)),where=good)
    wc=1-wa-wb;hits=np.flatnonzero(good&(wa>=-1e-5)&(wb>=-1e-5)&(wc>=-1e-5))
    if not len(hits):raise ValueError('Towel hem falls outside its cloth')
    i=max(hits,key=lambda j:wa[j]*a[j,1]+wb[j]*b[j,1]+wc[j]*c[j,1])
    normal=np.cross(b[i]-a[i],c[i]-a[i]);normal/=np.linalg.norm(normal)
    if normal[1]<0:normal=-normal
    return wa[i]*a[i,1]+wb[i]*b[i,1]+wc[i]*c[i,1],normal


def fabric_image():
    """Seamless albedo weave; no baked directional shadows or per-club copies."""
    size=512;y,x=np.mgrid[:size,:size]
    warp=np.cos(x*math.tau/8);weft=np.cos(y*math.tau/8)
    loops=np.sin(x*math.tau/16+y*math.tau/16)
    rng=np.random.default_rng(20261110)
    variation=7.8*warp+7.2*weft+2.7*loops+rng.normal(0,.9,(size,size))
    base=np.array([230.,229.,222.])
    rgb=np.clip(base+variation[:,:,None],0,255).astype('uint8')
    return Image.fromarray(np.dstack((rgb,np.full((size,size),255,dtype='uint8'))))


def seam_image():
    image=Image.new('RGBA',(128,64),(199,196,185,255));draw=ImageDraw.Draw(image)
    for y in (10,52):
        draw.line((0,y,127,y),fill=(201,199,190,255),width=1)
        for x in range(0,128,8):
            draw.line((x,y-2,x+4,y-2),fill=(240,239,231,255),width=2)
    return image
