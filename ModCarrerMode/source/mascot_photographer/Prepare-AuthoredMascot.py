from pathlib import Path
import sys,json,struct,io,hashlib,importlib.util
import numpy as np
from PIL import Image
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
parser.add_argument('--tools',required=True);parser.add_argument('--clips',required=True)
parser.add_argument('--club-id',type=int,required=True);parser.add_argument('--club-name',required=True)
parser.add_argument('--texture-template',required=True)
args=parser.parse_args()
ROOT=Path(args.output);TOOLS=Path(args.tools);SRC=Path(args.source)
sys.path[:0]=[str(TOOLS),str(TOOLS/'vendor/rx3tools'),str(Path(__file__).resolve().parent)]
from rx3 import Rx3,read_model,TEXTURE
from texture_assets import rx3_colour_png
from audit_locomotion import matrices,retarget,skin,foot_markers,audit
dest=ROOT/'package/data/sceneassets/mascot'/str(args.club_id)
rx=Rx3(Path(args.texture_template).read_bytes())
def texture(image,limit,mips=None):
    image=image.convert('RGBA');image.thumbnail((limit,limit),Image.Resampling.LANCZOS)
    w,h=image.size
    if w!=h or w&(w-1):raise ValueError('Power-of-two square texture required')
    data=bytearray(rx.get(TEXTURE)[0][:16]);data[5]=2
    count=0
    while True:
        out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT5');payload=out.getvalue()[128:]
        pitch=max(1,(image.width+3)//4)*16;rows=max(1,(image.height+3)//4)
        if len(payload)!=pitch*rows:raise ValueError('DDS block size mismatch')
        data.extend(struct.pack('<4I',pitch,rows,len(payload),0));data.extend(payload);count+=1
        if image.width==1 or (mips and count>=mips):break
        image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    struct.pack_into('<I',data,0,len(data));struct.pack_into('<4H',data,8,w,h,1,count)
    return bytes(data)
sections=[s for s in rx.sections if s[0]==TEXTURE]
sections[0][1]=texture(Image.open(next((p for p in SRC.rglob('*') if p.is_file() and ('basecolor' in p.name.lower() or 'tripo_rgb' in p.name.lower())))),2048)
sections[2][1]=texture(Image.open(next(p for p in SRC.rglob('*') if p.is_file() and 'normal' in p.name.lower())),1024)
(dest/'textures.rx3').write_bytes(rx.build())
(ROOT/'exported_basecolor.png').write_bytes(rx3_colour_png(dest/'textures.rx3'))
parts,raw=read_model(Rx3((dest/'model_animated.rx3').read_bytes()));part=parts[0];bind=matrices(raw)
(dest/'locomotion_feet.bin').write_bytes(foot_markers(part,bind))
(dest/'club.json').write_text(json.dumps(dict(id=args.club_id,name=args.club_name,importedFrom=next(SRC.glob('*.fbx')).name,rig='FIFA16 31 bones; preserved Mixamo weights; rigid head; independent limbs'),ensure_ascii=False,indent=2),encoding='utf8')
clips=Path(args.clips)
poseData={'bind':np.array(part['positions']).reshape(-1,3).tolist()};report={}
for label in ('idle','walk','cheer'):
    clip=json.loads((clips/(label+'_baked.json')).read_text());ref=matrices(json.loads((clips/'walk_baked.json').read_text())['referenceBind'])
    for fraction in (.0,.25,.5,.75):
        frame=clip['frames'][min(len(clip['frames'])-1,round((len(clip['frames'])-1)*fraction))]
        posed=skin(part,retarget(frame,ref,bind),bind,np.arange(len(part['positions'])//3))
        if not np.isfinite(posed).all():raise ValueError('Nonfinite animated mesh')
        poseData[label+str(fraction)]=posed.tolist()
    report[label]={'duration':clip['duration'],'frames':len(clip['frames'])}
    if label=='walk':report['locomotion']=audit(part,bind,ref,clip)
(ROOT/'poses.json').write_text(json.dumps(poseData),encoding='utf8')
weights=np.array(part['weights']).reshape(-1,4);joints=np.array(part['joints']).reshape(-1,4)
assert np.all(weights.sum(axis=1)==255) and np.all(joints<31)
xyz=np.array(part['positions']).reshape(-1,3)
for positive,chain in ((True,[3,4,5,6]),(False,[7,8,9,10])):
    ids=(xyz[:,1]<bind[2,1,3]*.8)&((xyz[:,0]>8) if positive else (xyz[:,0]<-8))
    assert not np.any(weights[ids]*np.isin(joints[ids],chain))
report['vertexCount']=len(weights);report['triangles']=len(part['indices'])//3;report['bones']=len(raw)
report['files']={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in dest.iterdir()}
for s in Rx3((dest/'textures.rx3').read_bytes()).get(TEXTURE):
    w,h,d,n=struct.unpack_from('<4H',s,8);p=16
    for level in range(n):
        pitch,rows,size,reserved=struct.unpack_from('<4I',s,p)
        assert pitch==max(1,(w+3)//4)*16 and rows==max(1,(h+3)//4) and size==pitch*rows
        p+=16+size;w=max(1,w//2);h=max(1,h//2)
    assert p<=len(s) and len(s)-p<16
(ROOT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('READY',report['vertexCount'],report['triangles'],report['locomotion']['strideCm'])
