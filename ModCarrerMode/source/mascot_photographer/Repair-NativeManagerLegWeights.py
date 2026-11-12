"""Review lower-body skin only, retaining RX3 geometry, UVs and bind byte-for-byte.

Run on a staged package. Reconstruct a smooth same-leg field from a working
native manager, keep the central crotch transition, and fade into the existing
pelvis. Upper body and feet are outside this correction.
"""
from pathlib import Path
import argparse,json,sys,struct,shutil
import numpy as np
from scipy.spatial import cKDTree

def smooth(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1);return t*t*(3-2*t)

def field(part):
    j=np.array(part['joints']).reshape(-1,4);w=np.array(part['weights']).reshape(-1,4)/255;out=np.zeros((len(j),31))
    for k in range(4):np.add.at(out,(np.arange(len(j)),j[:,k]),w[:,k])
    return out

def reviewed_field(points,original,reference_points,reference_field,trousers):
    # Retain the shoe/ankle fit and the accepted torso. Only trouser legs
    # and the lower pelvis transition receive the native reference field.
    # Keep the valid outer-leg/knee/calf skin. The observed flap originates
    # in the medial thigh/crotch, where opposite-leg neighbours overlapped.
    medial=1-smooth(7,13,abs(points[:,0]))
    focus=smooth(58,70,points[:,1])
    amount=medial*focus*(1-smooth(94,103,points[:,1]))*trousers
    indices=np.where(amount>0)[0];q=points[indices];side_fields=[]
    for side,chain in [(-1,[3,4,5]),(1,[7,8,9])]:
        eligible=(reference_points[:,1]<111)&(reference_points[:,0]*side>-.3)
        ref=reference_points[eligible];mass=reference_field[eligible].copy();allowed=[2,*chain,11];other=np.ones(31,dtype=bool);other[allowed]=False;mass[:,other]=0;total=mass.sum(1);ref=ref[total>.1];mass=mass[total>.1];mass/=mass.sum(1)[:,None]
        distance,near=cKDTree(ref).query(q,k=12);weights=1/(distance+.55)**2;weights/=weights.sum(1)[:,None];side_fields.append((mass[near]*weights[:,:,None]).sum(1))
    # Blend across the actual centre seam only. A broad nearest-neighbour
    # kernel must not pull one trouser leg with the opposite thigh.
    lateral=smooth(-2,2,q[:,0]);target=side_fields[0]*(1-lateral[:,None])+side_fields[1]*lateral[:,None]
    # The legs do not borrow upper-spine weights below the hip. Fade that
    # field into the unmodified pelvis/waist rather than imposing a hard cut.
    target[:,2]+=target[:,11];target[:,11]=0
    out=original.copy();out[indices]=original[indices]*(1-amount[indices,None])+target*amount[indices,None]
    return out,amount

def run(a):
    sys.path.insert(0,a.tools)
    from rx3 import Rx3,read_model,VERTEX,FORMAT
    before=Path(a.before);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);reference,_=read_model(Rx3(Path(a.reference).read_bytes()));rp=np.array(reference[0]['positions']).reshape(-1,3);rf=field(reference[0]);jobs=json.loads(Path(a.jobs).read_text(encoding='utf8'));reports=[]
    for job in jobs:
        if a.ids and job['coach_id'] not in a.ids:continue
        name=f'specificmanager_{job["club_id"]}_0_0.rx3';rx=Rx3((before/name).read_bytes());parts,bind=read_model(rx);part=parts[0];points=np.array(part['positions']).reshape(-1,3);original=field(part);uv=np.array(part['uvs']).reshape(-1,2)
        # Read the actual trouser chart from knee/calf vertices. Some supplied
        # atlases put trousers in a different cell. A spatial height cutoff
        # alone would also repaint the hem of a long jacket.
        # Hands can reach knee height in the authored bind pose. Sample the
        # actual calf skin, and allow trousers that span adjacent atlas cells.
        calf_mass=original[:,4]+original[:,8]
        sample=(points[:,1]>30)&(points[:,1]<65)&(calf_mass>.5)
        assert sample.any(), 'No weighted calf sample for trouser chart'
        cells=np.clip((uv[sample]*3).astype(int),0,2);counts=np.bincount(cells[:,0]*3+cells[:,1],minlength=9)
        selected_cells=np.where(counts/counts.sum()>.01)[0];assert counts[selected_cells].sum()/counts.sum()>.98
        trousers=np.zeros(len(points),dtype=bool);chart_cells=[]
        for cell in selected_cells:
            col,row=divmod(int(cell),3);chart_cells.append([col,row])
            trousers|=(uv[:,0]>=col/3-.001)&(uv[:,0]<=(col+1)/3+.001)&(uv[:,1]>=row/3-.001)&(uv[:,1]<=(row+1)/3+.001)
        reviewed,amount=reviewed_field(points,original,rp,rf,trousers)
        preserved=job['type']=='.rx3' or job['coach_id'] in a.preserve
        if preserved:reviewed=original.copy();amount[:]=0
        oldj=np.array(part['joints']).reshape(-1,4);oldw=np.array(part['weights']).reshape(-1,4);js=oldj.copy();ws=oldw.copy();active=amount>0
        chosen=np.argsort(-reviewed[active],axis=1)[:,:4];mass=np.take_along_axis(reviewed[active],chosen,axis=1);quant=np.rint(mass/mass.sum(1)[:,None]*255).astype(int);quant[:,0]+=255-quant.sum(1);js[active]=chosen;ws[active]=quant
        # Equal-position UV seams must follow exactly the same skin field.
        # Keep tiny 1.5 mm garment reverse surfaces independent: they already
        # receive the same spatial reference, without joining different layers.
        groups={}
        for i in np.where(active)[0]:groups.setdefault(tuple(points[i]),[]).append(i)
        for ids in groups.values():
            if len(ids)>1:js[ids]=js[ids[0]];ws[ids]=ws[ids[0]]
        vb=next(s for s in rx.sections if s[0]==VERTEX);raw=bytearray(vb[1]);stride=struct.unpack_from('<I',raw,8)[0];fields={}
        for token in rx.get(FORMAT)[0][16:].split(b'\0')[0].decode().split():
            semantic,offset,_,_,_=token.split(':');fields[semantic]=int(offset,16)
        for i in np.where(active)[0]:
            at=16+i*stride;raw[at+fields['i0']:at+fields['i0']+4]=js[i].astype('u1').tobytes();raw[at+fields['w0']:at+fields['w0']+4]=ws[i].astype('u1').tobytes()
        vb[1]=bytes(raw);blob=rx.build() if active.any() else (before/name).read_bytes();checked,cb=read_model(Rx3(blob));check=checked[0];assert cb==bind
        for key in ['positions','normals','uvs','indices']:assert check[key]==part[key],key
        assert np.array_equal(np.array(check['joints']).reshape(-1,4),js)
        assert np.array_equal(np.array(check['weights']).reshape(-1,4),ws)
        assert (ws.sum(1)==255).all();assert rx.get(0x0f3861a2)==Rx3((before/name).read_bytes()).get(0x0f3861a2)
        for weather in [0,1]:
            model=f'specificmanager_{job["club_id"]}_0_{weather}.rx3';(out/model).write_bytes(blob);tex=model[:-4]+'_textures.rx3';shutil.copy2(before/tex,out/tex)
        changed=(np.abs(reviewed-original).sum(1)>.01)&active;report={'coachId':job['coach_id'],'clubId':job['club_id'],'name':job['display_name'],'trouserAtlasCells':chart_cells,'reviewedVertices':int(active.sum()),'changedWeightVertices':int(changed.sum()),'nativeAuthoredLegSkinPreserved':job['type']=='.rx3','preservedAfterPoseReview':job['coach_id'] in a.preserve,'positionsNormalsUvsIndicesPreserved':True,'nativeBindPalettePreserved':True,'upperBodyPreserved':bool(np.array_equal(js[~active],oldj[~active]) and np.array_equal(ws[~active],oldw[~active])),'shoeGeometryAndWeightsPreserved':bool(np.array_equal(js[points[:,1]<=12],oldj[points[:,1]<=12]) and np.array_equal(ws[points[:,1]<=12],oldw[points[:,1]<=12])),'runtimeValidated':False};reports.append(report);print(json.dumps(report,ensure_ascii=True),flush=True)
    Path(a.report).write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--output',required=True);p.add_argument('--reference',required=True);p.add_argument('--jobs',required=True);p.add_argument('--report',required=True);p.add_argument('--tools',required=True);p.add_argument('--ids',nargs='*',type=int);p.add_argument('--preserve',nargs='*',type=int,default=[],help='Keep authored skin for models rejected by pose comparison');run(p.parse_args())
