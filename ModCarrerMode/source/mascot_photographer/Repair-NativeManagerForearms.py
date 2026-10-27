"""Bake the source's bare forearm appearance around its inconsistent sleeves.

The Tripo source has bare forearms in front and long shirt sleeves behind.
Project existing skin texels in source-space onto the cloth-painted back of
each forearm. UV layout and authored geometry stay unchanged.
This is an offline texture bake, not a runtime skin or animation override.
"""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image,ImageDraw
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt

def smooth(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)

def bake(surface,basecolor,normal,output,clean_cuff=False):
    data=json.loads(Path(surface).read_text(encoding='utf8'))
    vertices=np.array([row['position'] for row in data['vertices']])
    colors=np.asarray(Image.open(basecolor).convert('RGB')).copy()
    normals=np.asarray(Image.open(normal).convert('RGB')).copy()
    h,w=colors.shape[:2]
    if normals.shape!=colors.shape:raise ValueError('Color and normal atlas dimensions differ')
    positions=np.zeros((h,w,3),dtype=np.float32)
    occupied=Image.new('1',(w,h));draw=ImageDraw.Draw(occupied)
    valid=np.zeros((h,w),dtype=bool);offset=0
    for face in data['faces']:
        uv=np.array(data['uvs'][offset:offset+len(face)]);offset+=len(face)
        pixels=uv*np.array([w,-h])+np.array([0,h])
        draw.polygon([tuple(p) for p in pixels],fill=1)
        points=vertices[face]
        # Both authored arms are horizontal. Keep the torso and fingers out.
        if not (np.abs(points[:,0]).max()>(41 if clean_cuff else 47) and np.abs(points[:,0]).min()<73 and points[:,1].min()>130):continue
        for k in range(1,len(face)-1):
            ids=[0,k,k+1];tri=pixels[ids];p=points[ids]
            lo=np.maximum(np.floor(tri.min(0)).astype(int),[0,0]);hi=np.minimum(np.ceil(tri.max(0)).astype(int),[w-1,h-1])
            if np.any(hi<lo):continue
            xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
            q=np.stack((xx+.5-tri[0,0],yy+.5-tri[0,1]),axis=-1)
            matrix=np.stack((tri[1]-tri[0],tri[2]-tri[0]),axis=1)
            if abs(np.linalg.det(matrix))<1e-8:continue
            ab=q@np.linalg.inv(matrix).T
            bary=np.dstack((1-ab.sum(2),ab))
            inside=(bary.min(2)>=-1e-5)
            rows,cols=yy[inside],xx[inside]
            positions[rows,cols]=bary[inside]@p;valid[rows,cols]=True
    x=np.abs(positions[:,:,0]);rgb=colors.astype(float)
    # Native source has rolled cuffs at approximately 49 cm from center.
    # Preserve existing skin, including veins; replace only the cloth paint.
    # Cover the old cuff at the wrist completely; fading through that cuff
    # would leave a dark bracelet. Finger geometry starts beyond this band.
    envelope=smooth(49,51,x)*(1-smooth(70,72,x))*valid
    skin=smooth(6,17,rgb[:,:,0]-rgb[:,:,1])*smooth(0,8,rgb[:,:,1]-rgb[:,:,2])
    alpha=envelope*(1-skin)
    changed=np.zeros((h,w),dtype=bool);report={}
    for side in (-1,1):
        sideMask=positions[:,:,0]*side>0
        refs=valid&sideMask&(x>50)&(x<65)&(skin>.97)&(rgb[:,:,0]>110)
        # Only front skin supplies colors, never the hand or opposite arm.
        centerZ=-9.1+(x-45.4)*(-1.6/20)
        refs&=positions[:,:,2]>centerZ
        target=sideMask&(alpha>.001)
        if refs.sum()<100 or target.sum()<100:raise ValueError('Insufficient forearm atlas coverage')
        tree=cKDTree(positions[refs,:2]);dist,nearest=tree.query(positions[target,:2])
        if np.percentile(dist,99)>8:raise ValueError('Skin projection falls outside source forearm')
        reference=rgb[refs][nearest];a=alpha[target,None]
        colors[target]=np.rint(rgb[target]*(1-a)+reference*a).astype(np.uint8)
        # Cloth normal folds must not survive on newly exposed skin. Neutral
        # tangent normal is valid across the different destination UV charts.
        normals[target]=np.rint(normals[target].astype(float)*(1-a)+np.array([128,128,255])*a).astype(np.uint8)
        changed|=target
        report['left' if side>0 else 'right']=dict(referenceSkinTexels=int(refs.sum()),repaintedTexels=int(target.sum()),projectionDistanceP99Cm=float(np.percentile(dist,99)))
        if clean_cuff:
            # Rebuild one narrow material boundary all the way around the
            # cuff. The old 49..51 cm fade mixed shirt grey with skin, leaving
            # a dirty band; the source also has isolated skin below that edge.
            band=smooth(46.8,47.4,x)*(1-smooth(51.5,52.5,x))*valid*sideMask
            cuff=band>.001
            cloth=valid&sideMask&(x>43)&(x<46.5)&(skin<.1)&(rgb[:,:,0]>15)&(rgb[:,:,0]<110)
            skinRefs=refs&(x>52)&(x<60)
            if cloth.sum()<100 or skinRefs.sum()<100:raise ValueError('Insufficient cuff references')
            query=positions[cuff].copy();query[:,0]=np.clip(np.abs(query[:,0]),43,46)*side
            dist,ids=cKDTree(positions[cloth]).query(query,k=8)
            weight=1/np.maximum(dist,.15)**2;weight/=weight.sum(1,keepdims=True)
            clothColor=(rgb[cloth][ids]*weight[:,:,None]).sum(1)
            query=positions[cuff].copy();query[:,0]=np.clip(np.abs(query[:,0]),52.5,59.5)*side
            dist,ids=cKDTree(positions[skinRefs,:2]).query(query[:,:2],k=8)
            weight=1/np.maximum(dist,.15)**2;weight/=weight.sum(1,keepdims=True)
            skinColor=(rgb[skinRefs][ids]*weight[:,:,None]).sum(1)
            boundary=smooth(48.85,49.2,x[cuff])[:,None]
            desired=clothColor*(1-boundary)+skinColor*boundary
            blend=band[cuff,None]
            colors[cuff]=np.rint(colors[cuff].astype(float)*(1-blend)+desired*blend).astype(np.uint8)
            normals[cuff]=np.rint(normals[cuff].astype(float)*(1-blend)+np.array([128,128,255])*blend).astype(np.uint8)
            changed|=cuff
            report['left' if side>0 else 'right']['cleanCuffTexels']=int(cuff.sum())
            alpha=np.maximum(alpha,band)
    # Pad chart borders without overwriting any other occupied UV island.
    distance,nearest=distance_transform_edt(~changed,return_indices=True)
    padding=(distance<=(8 if clean_cuff else 3))&(~np.asarray(occupied,dtype=bool))
    for atlas in (colors,normals):atlas[padding]=atlas[nearest[0][padding],nearest[1][padding]]
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    Image.fromarray(colors).save(output/'forearms_basecolor.png')
    Image.fromarray(normals).save(output/'forearms_normal.png')
    Image.fromarray(np.rint(alpha*255).astype(np.uint8)).save(output/'forearms_repaint_mask.png')
    Image.fromarray((changed|padding).astype(np.uint8)*255).save(output/'forearms_write_mask.png')
    report.update(method='Source-space skin projection to inconsistent cloth-painted forearms and wrist cuff',cleanCuffBoundary=clean_cuff,cuffBoundaryCm=[48.85,49.2] if clean_cuff else None,faceOutsideRepair=True,geometryAndSkinWeightsUnchanged=True,texturePaddingTexels=int(padding.sum()))
    (output/'forearms_repair.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--surface',required=True);p.add_argument('--basecolor',required=True);p.add_argument('--normal',required=True);p.add_argument('--output',required=True);p.add_argument('--clean-cuff',action='store_true')
    a=p.parse_args();bake(a.surface,a.basecolor,a.normal,a.output,a.clean_cuff)
