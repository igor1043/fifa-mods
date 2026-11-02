"""Repair converted managers against their source geometry; keep native bind/UVs.

The input is the audited 20-coach manifest and its source vertex maps. Stage
outputs separately, then inspect native crossed-arm poses before installation.
Native RX3 reference feet are deliberately excluded from FBX foot correction.
"""
from pathlib import Path
import argparse,sys,json,struct,shutil
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.spatial import cKDTree

def align(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);s=np.linalg.norm(v);c=np.dot(a,b)
    if s<1e-9:return np.eye(3)
    return Rotation.from_rotvec(v/s*np.arctan2(s,c)).as_matrix()

def pack(v):
    q=np.rint(np.clip(v,-1,1)*511).astype(np.int64)&1023
    return (q[:,0]|q[:,1]<<10|q[:,2]<<20).astype('<u4')

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def run(a):
    sys.path.insert(0,a.tools)
    from rx3 import Rx3,read_model,VERTEX,INDEX,FORMAT
    prior=Path(a.prior);before=Path(a.before);stage=Path(a.output);dest=stage/'data/sceneassets/slc';dest.mkdir(parents=True,exist_ok=True);reports=[]
    for job in json.loads((prior/'jobs.json').read_text(encoding='utf8')):
        cid=job['coach_id']
        if a.ids and cid not in a.ids:continue
        name=f'specificmanager_{job["club_id"]}_0_0.rx3';rx=Rx3((before/name).read_bytes());parts,bind=read_model(rx);p=parts[0]
        xyz=np.array(p['positions']).reshape(-1,3).copy();uv=np.array(p['uvs']).reshape(-1,2);n=np.array(p['normals']).reshape(-1,3);j=np.array(p['joints']).reshape(-1,4);w=np.array(p['weights']).reshape(-1,4);tri=np.array(p['indices']).reshape(-1,3)
        baseline=read_model(Rx3((prior/'converted'/str(cid)/'package/data/sceneassets/slc'/name).read_bytes()))[0][0]
        n=np.array(baseline['normals']).reshape(-1,3)
        native=np.array(bind).reshape(-1,4,4)[:,3,:3];r={'coachId':cid,'clubId':job['club_id'],'sourceType':job['type'],'nativeBindUnchanged':True,'uvsPreserved':True,'runtimeValidated':False}
        if job['type']=='.fbx':
            profile=json.loads((prior/'converted'/str(cid)/'profile.json').read_text());mapping=np.array(json.loads((prior/'converted'/str(cid)/'source_vertex_map.json').read_text()));source=np.load(prior/'sources'/str(cid)/'source.npz')['positions']*profile.get('unitCorrection',1);orig=source[mapping];bones={int(k):np.array(v) for k,v in profile['sourceJointsCm'].items()}
            # Lower jaw belongs to the head, not to a collar/neck contraction.
            mask=(uv[:,0]>.666)&(uv[:,1]<.334)&(orig[:,1]>bones[14][1]-18)
            mass=smooth(bones[14][1]-12,bones[14][1]-6,orig[:,1])*mask
            rot=align(bones[15]-bones[14],native[15]-native[14]);head=(orig-bones[14])@rot.T+native[14]
            old=xyz.copy();xyz=xyz*(1-mass[:,None])+head*mass[:,None]
            jawDisplacement=float(np.linalg.norm((xyz-old)[mass>0],axis=1).max(initial=0))
            field=np.zeros((len(xyz),31))
            for k in range(4):np.add.at(field,(np.arange(len(xyz)),j[:,k]),w[:,k]/255)
            field*=1-mass[:,None];field[:,14]+=mass
            if a.reference_cloth_skin:
                reference=read_model(Rx3((prior/'reference/specificmanager_1043_0_0.rx3').read_bytes()))[0][0]
                rp=np.array(reference['positions']).reshape(-1,3);rj=np.array(reference['joints']).reshape(-1,4);rw=np.array(reference['weights']).reshape(-1,4)/255
                ends={2:11,11:12,12:13,13:14,14:15,3:4,4:5,5:6,7:8,8:9,9:10,16:17,17:18,18:19,19:20,21:22,22:23,23:24,24:25};fits=np.repeat(np.eye(4)[None],31,axis=0)
                for bone,end in ends.items():
                    axis=bones[end]-bones[bone];target=native[end]-native[bone];rot=align(axis,target);ratio=1 if bone in (2,11,12,13,14,19,24) else np.linalg.norm(target)/np.linalg.norm(axis);direction=axis/np.linalg.norm(axis);linear=rot@(np.eye(3)+(ratio-1)*np.outer(direction,direction));fits[bone,:3,:3]=linear;fits[bone,:3,3]=native[bone]-linear@bones[bone]
                fits[6]=fits[5];fits[10]=fits[9];inv=np.linalg.inv(fits);back=np.zeros_like(rp)
                for k in range(4):back+=((inv[rj[:,k],:3,:3]@rp[:,:,None])[:,:,0]+inv[rj[:,k],:3,3])*rw[:,k,None]
                distance,near=cKDTree(back).query(orig,k=16);coeff=1/(distance+.8)**2;coeff/=coeff.sum(1)[:,None];referenceField=np.zeros((len(rp),31))
                for k in range(4):np.add.at(referenceField,(np.arange(len(rp)),rj[:,k]),rw[:,k])
                transferred=(referenceField[near]*coeff[:,:,None]).sum(1)
                clothVertex=(uv[:,0]<.666)&(uv[:,1]<.668)&(orig[:,1]>78)&(orig[:,1]<bones[13][1]+5)
                armSkin=(uv[:,0]>.666)&(uv[:,1]>.334)&(uv[:,1]<.668)&(orig[:,1]>85)&(orig[:,1]<158)
                reviewed=clothVertex|armSkin
                field[reviewed]=transferred[reviewed]
                # The concealed base of the neck must share the garment's
                # continuous field. A separate neck rotation otherwise pulls
                # a skin triangle out through a polo/jacket shoulder.
                neck=(uv[:,0]>.666)&(uv[:,1]<.334)&(orig[:,1]>bones[14][1]-24)&(orig[:,1]<bones[14][1]-10)
                neckMass=(1-smooth(bones[14][1]-15,bones[14][1]-10,orig[:,1]))*neck
                field=field*(1-neckMass[:,None])+transferred*neckMass[:,None]
                fitPoints=np.zeros_like(orig)
                for bone in range(31):fitPoints+=((orig@fits[bone,:3,:3].T)+fits[bone,:3,3])*field[:,bone,None]
                xyz[reviewed]=fitPoints[reviewed]
                xyz=xyz*(1-neckMass[:,None])+fitPoints*neckMass[:,None]
                radial=xyz-native[13];radial[:,1]=0;length=np.linalg.norm(radial,axis=1);xyz-=radial/np.maximum(length[:,None],1e-8)*np.minimum(.7,length*.08)[:,None]*neckMass[:,None]
                concealed=armSkin&(abs(orig[:,0])<20)&(orig[:,1]>115)
                inset=(1-smooth(16,20,abs(orig[:,0])))*concealed
                radial=xyz-native[12];radial[:,1]=0;length=np.linalg.norm(radial,axis=1);xyz-=radial/np.maximum(length[:,None],1e-8)*np.minimum(1.2,length*.1)[:,None]*inset[:,None]
                xyz[:,1]-=1.5*smooth(4,10,abs(orig[:,0]))*smooth(140,150,orig[:,1])*inset
                r['garmentWeightsFromNativeReference']=int(clothVertex.sum())
                r['exposedArmWeightsFromNativeReference']=int(armSkin.sum())
                r['concealedNeckWeightsMatched']=int((neckMass>0).sum())
                r['concealedTorsoSkinInset']=int((inset>0).sum())
            # A source shoe has a flat sole. Rotating it onto the foot-to-toe
            # joint axis tipped its heel up; translate it without that pitch,
            # and fade into the ankle rather than making a hard leg seam.
            footchanges=[]
            for foot,toe in [(5,6),(9,10)]:
                side=(orig[:,0]<0) if foot==5 else (orig[:,0]>0)
                m=(1-smooth(bones[foot][1]+3,bones[foot][1]+12,orig[:,1]))*side
                target=orig+native[foot]-bones[foot]
                # Keep the sole at the native reference shoe floor in rest.
                referenceFoot=read_model(Rx3((prior/'reference/specificmanager_1043_0_0.rx3').read_bytes()))[0][0]
                refp=np.array(referenceFoot['positions']).reshape(-1,3)
                # Both feet share the same floor; only the FBX shoe is moved.
                floor=float(refp[refp[:,1]<8,1].min());bottom=float(np.min(target[m>.99,1]));target[:,1]+=floor-bottom
                xyz=xyz*(1-m[:,None])+target*m[:,None]
                oldrot=align(bones[toe]-bones[foot],native[toe]-native[foot]);nn=n@oldrot;n=n*(1-m[:,None])+nn*m[:,None]
                footchanges.append({'foot':foot,'vertices':int((m>0).sum()),'removedPitchDegrees':float(np.degrees(np.arccos(np.clip(oldrot[1,1],-1,1))))})
            selected=np.argsort(-field,axis=1)[:,:4];weights=np.take_along_axis(field,selected,axis=1);weights=np.rint(weights/weights.sum(1)[:,None]*255).astype(int);weights[:,0]+=255-weights.sum(1);j=selected;w=weights
            r.update(jawSourceVertices=int((mass>0).sum()),maxJawRestorationCm=jawDisplacement,footCorrections=footchanges)
        else:r['footCorrections']=[]
        # Correct existing triangle winding against the authored normals,
        # before calculating the shell. Do not infer outward from a folded
        # pose: the indexed topology must stay consistent across frames.
        cross=np.cross(xyz[tri[:,1]]-xyz[tri[:,0]],xyz[tri[:,2]]-xyz[tri[:,0]]);flip=(cross*n[tri].mean(1)).sum(1)<0;tri[flip]=tri[flip][:,[0,2,1]]
        r['correctedWindingFaces']=int(flip.sum())
        # The upper clothing charts include jacket and shirt. Give those
        # thin surfaces a physical reverse face, retaining independent UVs
        # for each layer. This prevents backface holes when sleeves fold.
        cloth=((uv[tri][:,:,0]<.666).all(1)&(uv[tri][:,:,1]<.668).all(1)&(xyz[tri][:,:,1]>76).all(1)&(xyz[tri][:,:,1]<165).all(1))
        ids=np.unique(tri[cloth]);count=len(xyz);innerMap=np.full(count,-1,dtype=int);innerMap[ids]=np.arange(len(ids))+count
        if count+len(ids)>=65536:raise ValueError((cid,'16-bit vertex budget exceeded',count,len(ids)))
        # Retain authored split normals and independent UVs on the garment
        # layers. The reverse surface is 1.5 mm inside the original surface.
        unit=n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-8)
        xyz=np.r_[xyz,xyz[ids]-unit[ids]*.15];n=np.r_[unit,-unit[ids]];uv=np.r_[uv,uv[ids]];j=np.r_[j,j[ids]];w=np.r_[w,w[ids]]
        inner=innerMap[tri[cloth]][:,[0,2,1]];tri=np.r_[tri,inner]
        r.update(garmentInnerVertices=len(ids),garmentReverseFaces=len(inner),garmentThicknessCm=.15,vertices=len(xyz),triangles=len(tri))
        # Recalculate tangents from the edited positions with independent
        # front/back vertices. Keep normals and split UV boundaries intact.
        pts=xyz[tri];e1=pts[:,1]-pts[:,0];e2=pts[:,2]-pts[:,0];d1=uv[tri[:,1]]-uv[tri[:,0]];d2=uv[tri[:,2]]-uv[tri[:,0]];det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0];tg=(e1*d2[:,1,None]-e2*d1[:,1,None])/np.where(abs(det)>1e-10,det,1)[:,None];tg[abs(det)<=1e-10]=0;tangent=np.zeros_like(xyz)
        for k in range(3):np.add.at(tangent,tri[:,k],tg)
        tangent-=n*np.sum(tangent*n,axis=1,keepdims=True);bad=np.linalg.norm(tangent,axis=1)<1e-8;tangent[bad]=np.cross(n[bad],np.where((abs(n[bad,0])>.9)[:,None],[0,1,0],[1,0,0]));tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-8)
        vb=next(s for s in rx.sections if s[0]==VERTEX);stride=struct.unpack_from('<I',vb[1],8)[0];fields={}
        for token in rx.get(FORMAT)[0][16:].split(b'\0')[0].decode().split():
            name,offset,_,_,fmt=token.split(':');fields[name]=int(offset,16)
        size=(16+stride*len(xyz)+15)&~15;data=bytearray(size);struct.pack_into('<4I',data,0,size,len(xyz),stride,1);pn=pack(n);pt=pack(tangent)
        for i in range(len(xyz)):
            at=16+i*stride;struct.pack_into('<4e',data,at+fields['p0'],*xyz[i],1);struct.pack_into('<I',data,at+fields['n0'],pn[i]);struct.pack_into('<I',data,at+fields['g0'],pt[i]);struct.pack_into('<2e',data,at+fields['t0'],*uv[i]);data[at+fields['i0']:at+fields['i0']+4]=bytes(j[i].tolist());data[at+fields['w0']:at+fields['w0']+4]=bytes(w[i].tolist())
        vb[1]=bytes(data);flat=tri.reshape(-1);size=(16+len(flat)*2+15)&~15;ib=bytearray(size);struct.pack_into('<4I',ib,0,size,len(flat),2,0);ib[16:16+len(flat)*2]=flat.astype('<u2').tobytes();next(s for s in rx.sections if s[0]==INDEX)[1]=bytes(ib);instance=next(s for s in rx.sections if s[0]==0x22b2be36);data=bytearray(instance[1]);struct.pack_into('<3I',data,16,size,len(flat),2);instance[1]=bytes(data)
        result=rx.build();checked,cb=read_model(Rx3(result));assert cb==bind and len(checked[0]['positions'])//3==len(xyz);assert all(np.sum(w,axis=1)==255)
        for weather in [0,1]:
            model=f'specificmanager_{job["club_id"]}_0_{weather}.rx3';(dest/model).write_bytes(result);tex=model[:-4]+'_textures.rx3';shutil.copy2(before/tex,dest/tex)
        reports.append(r);print(json.dumps(r),flush=True)
    (stage.parent/'surface_repairs.json').write_text(json.dumps(reports,indent=2),encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior',required=True);p.add_argument('--before',required=True);p.add_argument('--output',required=True);p.add_argument('--tools',required=True);p.add_argument('--ids',nargs='*',type=int);p.add_argument('--reference-cloth-skin',action='store_true');run(p.parse_args())
