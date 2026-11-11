"""Offline conversion helpers for user-supplied, static room props (centimetres)."""
import math
import numpy as np
from PIL import Image


def rotation(degrees):
    angle=math.radians(degrees);c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]],dtype=float)


def transform(points,normals,pivot,destination,degrees=0,scale=1):
    if not np.isfinite(scale) or scale<=0:raise ValueError('Invalid prop scale')
    r=rotation(degrees)
    p=(np.asarray(points)-pivot)@r.T*scale+destination
    n=np.asarray(normals)@r.T
    n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-9)
    if not np.isfinite(p).all() or not np.isfinite(n).all():raise ValueError('Invalid prop geometry')
    return p,n


def without_coplanar_duplicates(parts):
    """SketchUp front/back materials can export the exact same face twice."""
    seen=set();result=[]
    for part in parts:
        p=np.asarray(part['p']);tri=np.asarray(part['idx']).reshape(-1,3);kept=[]
        for indices in tri:
            points=p[indices]
            if np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))<1e-7:continue
            key=tuple(sorted(tuple(row) for row in np.round(points,4)))
            if key in seen:continue
            seen.add(key);kept.extend(indices)
        if kept:result.append(dict(part,idx=np.array(kept,dtype=np.uint32)))
    return result


class Palette:
    """Wide gutters and constant UVs keep flat material colors stable at distance."""
    def __init__(self):self.colors=[]

    def uv(self,color,linear=False):
        c=np.clip(np.asarray(color[:3],float),0,1)
        if linear:c=np.where(c<=.0031308,c*12.92,1.055*np.power(c,1/2.4)-.055)
        color=tuple(np.rint(c*255).astype(int))+(255,)
        if color not in self.colors:self.colors.append(color)
        i=self.colors.index(color)
        if i>=64:raise ValueError('Palette exhausted')
        return ((i%8+.5)/8,(i//8+.5)/8)

    def image(self):
        out=Image.new('RGBA',(512,512),(180,180,180,255))
        for i,c in enumerate(self.colors):out.paste(c,(i%8*64,i//8*64,i%8*64+64,i//8*64+64))
        return out


def merged_parts(parts,vertex_limit=60000):
    """Weld all attributes together; preserve material seams and hard normals."""
    faces=[]
    for part in parts:
        triangles=np.asarray(part['idx']).reshape(-1,3).copy()
        points=part['p'][triangles]
        face=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])
        reverse=np.einsum('ij,ij->i',face,part['n'][triangles].mean(axis=1))<0
        triangles[reverse]=triangles[reverse][:,[0,2,1]]
        idx=triangles.reshape(-1)
        faces.append(np.concatenate([part['p'][idx],part['n'][idx],part['uv'][idx]],axis=1))
    vertices=np.concatenate(faces).astype('<f4')
    results=[];limit=vertex_limit//3*3
    for start in range(0,len(vertices),limit):
        unique,indices=np.unique(vertices[start:start+limit],axis=0,return_inverse=True)
        results.append(dict(positions=unique[:,:3],normals=unique[:,3:6],uvs=unique[:,6:8],indices=indices.astype(np.uint32)))
    return results
