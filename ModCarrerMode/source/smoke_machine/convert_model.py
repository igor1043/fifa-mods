"""Convert supplied static FBX mesh and textures using the validated FIFA static SLE layout."""
from pathlib import Path
import json,sys,struct,math,io,hashlib
import numpy as np
from PIL import Image,ImageOps
R=Path(__file__).resolve().parent
T=Path(r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster')
sys.path[:0]=[str(T),str(T/'vendor/rx3tools')]
from rx3 import Rx3,read_model,VERTEX,INDEX,MESH,TEXTURE,align
from texture_assets import rx3_colour_png
S=Path('C:/Users/igorv/OneDrive/\u00c1rea de Trabalho/maquina fuma\u00e7a')
D=R/'package/data/sceneassets/smoke_machine';D.mkdir(parents=True,exist_ok=True)
data=json.loads((R/'mesh_source.json').read_text());vertices=data['vertices'];indices=data['indices']
def packed(v):return sum((int(round(max(-1,min(1,x))*511))&1023)<<s for x,s in zip(v,(0,10,20)))
rx=Rx3(Path(r'U:\fifa 16\data\sceneassets\slc\specificcameramansitting_0_24_0.rx3').read_bytes())
vb=bytearray(align(16+20*len(vertices)));struct.pack_into('<4I',vb,0,len(vb),len(vertices),20,1)
for i,(p,n,t,uv) in enumerate(vertices):struct.pack_into('<4eII2e',vb,16+i*20,*p,1,packed(n),packed(t),*uv)
ib=bytearray(align(16+2*len(indices)));struct.pack_into('<4I',ib,0,len(ib),len(indices),2,0)
struct.pack_into('<'+'H'*len(indices),ib,16,*indices)
for sec in rx.sections:
    if sec[0]==VERTEX:sec[1]=bytes(vb)
    elif sec[0]==INDEX:sec[1]=bytes(ib)
    elif sec[0]==MESH:
        b=bytearray(sec[1]);struct.pack_into('<H',b,0,4);sec[1]=bytes(b)
    elif sec[0]==0x22B2BE36:
        b=bytearray(sec[1]);struct.pack_into('<III',b,16,len(ib),len(indices),2);sec[1]=bytes(b)
rx.set_names([(MESH,'smoke_machine_.FxRenderableSimple')]);(D/'model.rx3').write_bytes(rx.build())
parts,bones=read_model(Rx3((D/'model.rx3').read_bytes()));part=parts[0]
assert len(parts)==1 and not bones and len(part['positions'])==3*len(vertices) and max(part['indices'])<len(vertices)
assert all(math.isfinite(x) for x in part['positions']+part['uvs'])
position_error=max(abs(a-b) for i,v in enumerate(vertices) for a,b in zip(v[0],part['positions'][3*i:3*i+3]))
uv_error=max(abs(a-b) for i,v in enumerate(vertices) for a,b in zip(v[3],part['uvs'][2*i:2*i+2]))
assert position_error<.1 and uv_error<.001
p=np.array(part['positions']).reshape(-1,3);n=np.array(part['normals']).reshape(-1,3);f=np.array(part['indices']).reshape(-1,3)
dot=np.einsum('ij,ij->i',np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),n[f].mean(axis=1))
winding={'positive':int((dot>.001).sum()),'negative':int((dot<-.001).sum())}
assert winding['positive']>winding['negative']*10
tx=Rx3(Path(r'U:\fifa 16\data\sceneassets\mascot\1041\textures.rx3').read_bytes());secs=[s for s in tx.sections if s[0]==TEXTURE]
def texture(im,is_normal=False):
    im=im.convert('RGBA');w,h=im.size;assert w&(w-1)==0 and h&(h-1)==0
    b=bytearray(secs[0][1][:16]);b[5]=2;count=0
    while True:
        out=io.BytesIO();im.save(out,format='DDS',pixel_format='DXT5');raw=out.getvalue()[128:]
        pitch=max(1,(im.width+3)//4)*16;rows=max(1,(im.height+3)//4);assert len(raw)==pitch*rows
        b.extend(struct.pack('<4I',pitch,rows,len(raw),0));b.extend(raw);count+=1
        if im.width==im.height==1:break
        im=im.resize((max(1,im.width//2),max(1,im.height//2)),Image.Resampling.LANCZOS)
        if is_normal:
            a=np.array(im);vectors=a[:,:,:3].astype(np.float32)/127.5-1
            vectors/=np.maximum(np.linalg.norm(vectors,axis=2,keepdims=True),1e-8)
            a[:,:,:3]=np.clip(np.rint((vectors+1)*127.5),0,255).astype(np.uint8);a[:,:,3]=255;im=Image.fromarray(a)
    struct.pack_into('<I',b,0,len(b));struct.pack_into('<4H',b,8,w,h,1,count);return bytes(b)
src=S/'industrial+machine+3d+model.fbm'
colour=Image.open(src/'industrial+machine+3d+model_basecolor.jpg').convert('RGBA').resize((1024,1024),Image.Resampling.LANCZOS)
red,green,blue=Image.open(src/'industrial+machine+3d+model_normal.png').convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS).split()
normal=Image.merge('RGBA',(red,ImageOps.invert(green),blue,Image.new('L',(1024,1024),255)))
secs[0][1]=texture(colour);secs[1][1]=texture(Image.new('RGBA',(64,64),(18,35,0,255)));secs[2][1]=texture(normal,True)
tx.set_names([(TEXTURE,'smoke_machine_cm'),(TEXTURE,'smoke_machine_coeff'),(TEXTURE,'smoke_machine_nm')]);(D/'textures.rx3').write_bytes(tx.build())
checked=Rx3((D/'textures.rx3').read_bytes())
for section in checked.get(TEXTURE):
    w,h,d,count=struct.unpack_from('<4H',section,8);at=16
    assert count==int(math.log2(max(w,h)))+1
    for _ in range(count):
        pitch,rows,size,_=struct.unpack_from('<4I',section,at)
        assert pitch==max(1,(w+3)//4)*16 and rows==max(1,(h+3)//4) and size==pitch*rows
        at+=16+size;w=max(1,w//2);h=max(1,h//2)
    assert at==len(section)
(R/'colour_rx3.png').write_bytes(rx3_colour_png(D/'textures.rx3'))
(R/'converted_mesh.json').write_text(json.dumps(part),encoding='utf8')
report={'source':str(S),'vertices':len(vertices),'triangles':len(indices)//3,'static':True,'skeleton':False,
        'height_cm':data['height_cm'],'bounds_cm':[p.min(axis=0).tolist(),p.max(axis=0).tolist()],
        'position_error_cm':position_error,'uv_error':uv_error,'winding':winding,'textures':checked.names(),
        'normal_map_green_inverted':True,'normal_mips_renormalized':True,
        'source_files':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in S.rglob('*') if q.is_file()},
        'files':{q.name:{'size':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in D.glob('*.rx3')}}
(R/'conversion_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
