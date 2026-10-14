"""Native static RX3, supplied diffuse/normal plus separate mirror/frame cells."""
from pathlib import Path
import json,sys,struct,math,io,hashlib
import numpy as np
from PIL import Image,ImageOps
R=Path(__file__).resolve().parent
T=Path(r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster')
sys.path[:0]=[str(T),str(T/'vendor/rx3tools')]
from rx3 import Rx3,read_model,VERTEX,INDEX,MESH,TEXTURE,align
from texture_assets import rx3_colour_png
S=Path('C:/Users/igorv/OneDrive/\u00c1rea de Trabalho/CABINE DO VAR 2')
D=R/'package/data/sceneassets/var_cabin';D.mkdir(parents=True,exist_ok=True)
data=json.loads((R/'mesh_source.json').read_text(encoding='utf8'));vertices=data['vertices'];indices=data['indices']
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
rx.set_names([(MESH,'var_cabin_.FxRenderableSimple')]);(D/'model_v2.rx3').write_bytes(rx.build())
parts,bones=read_model(Rx3((D/'model_v2.rx3').read_bytes()));part=parts[0]
assert len(parts)==1 and not bones and len(part['positions'])==3*len(vertices) and max(part['indices'])<len(vertices)
assert all(math.isfinite(x) for x in part['positions']+part['uvs'])
position_error=max(abs(a-b) for i,v in enumerate(vertices) for a,b in zip(v[0],part['positions'][3*i:3*i+3]))
uv_error=max(abs(a-b) for i,v in enumerate(vertices) for a,b in zip(v[3],part['uvs'][2*i:2*i+2]))
assert position_error<.1 and uv_error<.001
p=np.array(part['positions']).reshape(-1,3);n=np.array(part['normals']).reshape(-1,3);f=np.array(part['indices']).reshape(-1,3)
dot=np.einsum('ij,ij->i',np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),n[f].mean(axis=1))
winding={'positive':int((dot>.001).sum()),'negative':int((dot<-.001).sum())};assert winding['positive']>winding['negative']*10
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
colour=Image.new('RGBA',(2048,4096),(28,33,38,255))
source_colour=Image.open(S/'CABINE+DO+VAR_basecolor.jpg').convert('RGBA');assert source_colour.size==(2048,2048)
colour.paste(source_colour,(0,0))
normal=Image.new('RGBA',(2048,4096),(128,128,255,255))
red,green,blue=Image.open(S/'CABINE+DO+VAR_normal.png').convert('RGB').split()
normal.paste(Image.merge('RGBA',(red,ImageOps.invert(green),blue,Image.new('L',(2048,2048),255))),(0,0))
coeff=Image.new('RGBA',(2048,4096),(18,35,0,255))
# Native coefficient inputs already connected to the character environment
# textures. Smooth mirror panels receive a stronger specular response than body.
colour.paste((218,222,225,255),(0,2048,512,3072));coeff.paste((48,85,0,255),(0,2048,512,3072))
colour.paste((19,21,24,255),(512,2048,1024,2560));coeff.paste((24,65,0,255),(512,2048,1024,2560))
colour.paste((14,28,165,255),(512,2560,1024,3072))
colour.paste((115,133,145,255),(1024,2048,2048,3072));coeff.paste((220,240,0,255),(1024,2048,2048,3072))
secs[0][1]=texture(colour);secs[1][1]=texture(coeff);secs[2][1]=texture(normal,True)
tx.set_names([(TEXTURE,'var_cabin_cm'),(TEXTURE,'var_cabin_coeff'),(TEXTURE,'var_cabin_nm')]);(D/'textures_v2.rx3').write_bytes(tx.build())
checked=Rx3((D/'textures_v2.rx3').read_bytes())
for section in checked.get(TEXTURE):
    w,h,d,count=struct.unpack_from('<4H',section,8);assert (w,h,count)==(2048,4096,13);at=16
    for _ in range(count):
        pitch,rows,size,_=struct.unpack_from('<4I',section,at);assert pitch==max(1,(w+3)//4)*16 and rows==max(1,(h+3)//4) and size==pitch*rows
        at+=16+size;w=max(1,w//2);h=max(1,h//2)
    assert at==len(section)
(R/'colour_rx3.png').write_bytes(rx3_colour_png(D/'textures_v2.rx3'))
(R/'converted_mesh.json').write_text(json.dumps(part),encoding='utf8')
report={'source':str(S/'Cabine do Var.obj'),'vertices':len(vertices),'triangles':len(indices)//3,'static':True,'skeleton':False,'height_cm':200,'bounds_cm':[p.min(axis=0).tolist(),p.max(axis=0).tolist()],'position_error_cm':position_error,'uv_error':uv_error,'winding':winding,'textures':checked.names(),'texture_size':[2048,4096],'diffuse_source_preserved_at_native_resolution':[2048,2048],'material_triangle_counts':data['material_triangle_counts'],'normal_map_green_inverted':True,'normal_mips_renormalized':True,'mirror_finish':'native environment/specular inputs, not planar real-time reflection','source_files':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in S.iterdir() if q.is_file()},'files':{q.name:{'size':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in D.iterdir() if q.suffix=='.rx3'}}
(R/'conversion_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');(D/'model_v2.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
