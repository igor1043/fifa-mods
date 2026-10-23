import portable_paths as portable
"""Trim only the medical annex's old left wall, retaining native UVs/normals."""
import numpy as np

def open_medical_annex(vertices,indices,left=-740.,opening=942.):
    result=[];faces=[]
    for face in indices.reshape(-1,3):
        triangle=[vertices[int(i)].copy() for i in face]
        if all(float(v['p'][0])<=left for v in triangle):
            polygon=[]
            for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                inside_a=float(a['p'][2])<=opening;inside_b=float(b['p'][2])<=opening
                if inside_a:polygon.append(a)
                if inside_a!=inside_b:
                    t=(opening-float(a['p'][2]))/float(b['p'][2]-a['p'][2]);v=a.copy()
                    for key in ('p','uv','n'):v[key]=a[key]+(b[key]-a[key])*t
                    polygon.append(v)
        else:polygon=triangle
        if len(polygon)<3:continue
        start=len(result);result.extend(polygon)
        for i in range(1,len(polygon)-1):faces.extend((start,start+i,start+i+1))
    return np.array(result,dtype=vertices.dtype),np.array(faces,dtype='<u4')
