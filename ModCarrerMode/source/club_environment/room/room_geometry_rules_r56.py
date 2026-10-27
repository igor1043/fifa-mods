import portable_paths as portable
import unicodedata,re
import numpy as np

def ceiling_outside_clinic(vertices,indices):
    """Remove the medical ceiling area, retaining interpolated native UVs."""
    output=[];faces=[]
    def clipped(poly,axis,bound,keep_high):
        result=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            va=float(a['p'][axis])-bound;vb=float(b['p'][axis])-bound
            ina=va>=0 if keep_high else va<=0;inb=vb>=0 if keep_high else vb<=0
            if ina:result.append(a)
            if ina!=inb:
                f=va/(va-vb);q=a.copy()
                for key in ('p','uv','n'):q[key]=a[key]+(b[key]-a[key])*f
                result.append(q)
        return result
    for ids in indices.reshape(-1,3):
        triangle=[vertices[i].copy() for i in ids]
        right=clipped(triangle,0,-330,True)
        front=clipped(clipped(triangle,0,-330,False),2,942,False)
        for poly in (right,front):
            if len(poly)<3:continue
            start=len(output);output.extend(poly)
            for i in range(1,len(poly)-1):faces.extend((start,start+i,start+i+1))
    return np.array(output,dtype=vertices.dtype),np.array(faces,dtype='<u4')
def old_medical(name):
    prefix=name.split(' / ',1)[0]
    key=re.sub('[^a-z]','',unicodedata.normalize('NFKD',prefix.casefold()))
    return key in ('areamedica','reamdica')
