"""Coach-only material separation; UV seams remain distinct from hair cards.

The supplied manager atlases have no authored hair alpha. Repeated UV strips
receive tapered strands; native heads with continuous paintings use a soft
background key. Body texels remain opaque. Scoped to the 20 audited compact
SLC managers; this is an approximate mask, not recovered author alpha.
"""
import copy
import re
import numpy as np
from PIL import Image,ImageFilter
from native_assets import decode

VERSION=5
CLUBS={1039,1035,1598,517,112476,1041,111044,568,1043,567,1629,1048,113163,383,123921,130026,1053,598,569,1719}

def manager(rig):
    if not (100000000<int(rig.get('id',0))<102000000 and len(rig['bones'])==31):return False
    if int(rig['id'])-100000000 in CLUBS:return True
    return any(re.fullmatch(r'data/sceneassets/(?:manager_market/[1-9][0-9]{0,5}/model_0|slc/specificmanager_[1-9][0-9]{0,5}_0_0)\.rx3',p.get('asset','')) for p in rig.get('parts',[]))

def hair_charts(v,tri):
    parent=np.arange(len(v))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for a,b,c in tri:
        root=find(int(a));parent[find(int(b))]=root;parent[find(int(c))]=root
    groups={}
    for i in np.unique(tri):groups.setdefault(find(int(i)),[]).append(int(i))
    boxes=[]
    for ids in groups.values():
        uv=v['uv'][ids];lo=uv.min(0);hi=uv.max(0)
        if min(hi-lo)>.004:boxes.append((lo,hi))
    if not boxes:return [],'color-key'
    widths=np.array([hi[0]-lo[0] for lo,hi in boxes]);rounded=np.rint(widths/.003).astype(int);mode=np.bincount(rounded).argmax();consistent=abs(widths-mode*.003)<.003
    # Repeated UV strips are different from native heads whose cards sample
    # arbitrary patches of one continuous hair painting. Never put a regular
    # comb mask over those native UVs.
    if consistent.mean()<.65 or consistent.sum()<5:return boxes,'color-key'
    return boxes,'strand-charts'

def _strands(width,height,seed):
    y=np.linspace(0,1,height)[:,None];x=np.linspace(0,1,width)[None,:];result=np.zeros((height,width),dtype=float)
    # Dense hidden roots preserve volume. Individually tapered, curved locks
    # make the visible end irregular instead of exposing a rectangular card.
    count=max(15,min(43,round(width/7)));pitch=.88/(count-1)
    for k in range(count):
        phase=(k*2.399963+seed*.73);tip=.74+.25*(.5+.5*np.sin(phase*1.7));center=.06+k*pitch+.0055*np.sin(y*4+phase)*y
        half=pitch*(.34*(1-y)**.8+.05);distance=abs(x-center);lock=np.clip((half-distance)/(pitch*.10),0,1)*np.clip((tip-y)/.045,0,1);result=np.maximum(result,lock)
    # Roots also need gaps: a solid root rectangle remains visible on models
    # whose cards sit above the scalp rather than beginning inside it.
    return np.rint(result*255).astype('u1')

def _color_key(rgb):
    patch=Image.fromarray(rgb);a=rgb.astype(float);blur=np.array(patch.filter(ImageFilter.GaussianBlur(2))).astype(float);detail=np.linalg.norm(a-blur,axis=2)
    flat=detail<np.percentile(detail,30);quant=(rgb//12).astype(int);keys=quant[:,:,0]*484+quant[:,:,1]*22+quant[:,:,2];counts=np.bincount(keys[flat].ravel(),minlength=10648);mode=counts.argmax();samples=a[flat&(keys==mode)];background=np.median(samples,axis=0) if len(samples) else np.median(a.reshape(-1,3),axis=0)
    distance=np.linalg.norm(a-background,axis=2);spread=float(np.percentile(np.linalg.norm(samples-background,axis=1),90)) if len(samples) else 2
    coverage=np.clip((distance-spread-2)/max(18,float(np.percentile(distance,85))-spread),0,1)**.45
    fibers=np.clip((detail-2)/16,0,1)**.55;coverage=np.maximum(coverage,fibers)
    mask=Image.fromarray(np.rint(coverage*255).astype('u1')).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.4))
    return np.array(mask)

def hair_matte(image,charts=None,layout='strand-charts',preserve_authored=False):
    data=np.array(image.convert('RGBA')).copy();h,w=data.shape[:2];alpha=np.full((h,w),255,dtype=np.uint8)
    y0=round(h*5/6);x0=round(w/3)
    if charts is None:charts=[(np.array([1/3+k/12,5/6]),np.array([1/3+(k+1)/12,1])) for k in range(8)]
    if not charts:charts=[(np.array([1/3,5/6]),np.array([1,1]))]
    authored=data[y0:,x0:,3]
    has_authored=bool(preserve_authored and (authored<220).mean()>.01 and (authored>240).mean()>.01)
    if has_authored:
        # Some native packages supply a real cutout. Keep its fibers; applying
        # a generated matte over those cards would thin the hair a second time.
        alpha[y0:,x0:]=authored
    elif layout=='color-key':
        lo=np.min([lo for lo,hi in charts],axis=0);hi=np.max([hi for lo,hi in charts],axis=0);left=max(x0,int(lo[0]*w));right=min(w,int(np.ceil(hi[0]*w)));top=max(y0,int(lo[1]*h));bottom=min(h,int(np.ceil(hi[1]*h)))
        if right>left and bottom>top:alpha[top:bottom,left:right]=_color_key(data[top:bottom,left:right,:3])
    else:
        alpha[y0:,x0:]=0;seen=set()
        for lo,hi in charts:
            left=max(x0,round(float(lo[0])*w));right=min(w,round(float(hi[0])*w));top=max(y0,round(float(lo[1])*h));bottom=min(h,round(float(hi[1])*h));key=(left,top,right,bottom)
            if key in seen or right<=left or bottom<=top:continue
            seen.add(key);mask=_strands(right-left,bottom-top,round(float(lo[0])*100))
            alpha[top:bottom,left:right]=np.maximum(alpha[top:bottom,left:right],mask)
    data[:,:,3]=alpha
    return data,{'hairMatteTexels':int((alpha<255).sum()),'nonHairAlphaOpaque':bool(np.all(alpha[:y0]==255)),'layout':layout,'denseRoots':True,'twoSidedCards':True,'sourceContainsAuthoredAlpha':has_authored,'approximateMask':not has_authored}

def prepare(rig):
    if not manager(rig):return rig,None
    rig=copy.deepcopy(rig);parts=[];reports=[];textures={}
    for part in rig['parts']:
        v=part['v'];tri=part['idx'].reshape(-1,3);uv=v['uv'][tri]
        # Inspect every corner to avoid pulling a face/neck seam into hair.
        # Half-float RX3 UVs can place a chart border a fraction below 1/3
        # or 5/6. Include that border, otherwise opaque slivers remain.
        is_hair=(uv[:,:,0]>.330).all(1)&(uv[:,:,1]>.828).all(1)&(v['p'][tri][:,:,1]>140).all(1)
        if not is_hair.any():parts.append(part);continue
        texture=part['texture']
        charts,layout=hair_charts(v,tri[is_hair])
        if texture not in textures:
            native_id=re.search(r'/(?:manager_market/([0-9]+)/|slc/specificmanager_([0-9]+)_0_0)',part.get('asset',''));source_id=int(next(x for x in native_id.groups() if x)) if native_id else 0;preserve_authored=(200<=source_id<=211 or 190200<=source_id<=190211)
            rgba,info=hair_matte(decode(rig['textures'][texture]),charts,layout,preserve_authored=preserve_authored);h,w=rgba.shape[:2];textures[texture]=len(rig['textures']);rig['textures'].append((w,h,3,rgba.tobytes()));reports.append(info)
        for mask,hair in [(~is_hair,False),(is_hair,True)]:
            if not mask.any():continue
            ids,inverse=np.unique(tri[mask].reshape(-1),return_inverse=True);p=dict(part);p['v']=v[ids].copy();p['idx']=inverse.astype('<u4');p['name']='manager_hair_cards' if hair else 'manager_opaque_body'
            if hair:
                p.update(texture=textures[texture],blend=1,coeff=-1,alpha=1.,asset=part['asset']+'/hair/cards')
                if layout=='strand-charts' and rig['bones'][14].get('rest') is not None:
                    # Converted cards carried independent planar normals,
                    # making every lock light up like a flat leaf. Blend the
                    # upper hair toward one head volume; leave beard normals
                    # and the opaque head/face untouched.
                    head=np.asarray(rig['bones'][14]['rest'])[:3,3];center=head+np.array([0,6,0]);radial=(p['v']['p']-center)/np.array([81,144,100]);radial/=np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),1e-8)
                    mass=np.clip((p['v']['p'][:,1]-head[1]-1)/7,0,1)[:,None]*.9;normal=p['v']['n']*(1-mass)+radial*mass;normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8);p['v']['n']=normal
                # Separate reverse-side vertices keep the normal sign correct
                # through the native winding/tangent encoder.
                back=p['v'].copy();back['n']*=-1;front=p['idx'].reshape(-1,3);p['idx']=np.r_[front,(front[:,[0,2,1]]+len(back))].reshape(-1).astype('<u4');p['v']=np.r_[p['v'],back]
            parts.append(p)
    rig['parts']=parts
    return rig,{'version':VERSION,'separateHairParts':sum('/hair/' in p['asset'] for p in parts),'opaqueBodyParts':sum('/hair/' not in p['asset'] for p in parts),'hairMasks':reports}
