import portable_paths as portable
"""Local experiment: scenery owns only custom geometry/textures.

Native kit, boots, balls, crests and print textures are referenced from FIFA.
Never modifies a save, a native asset or the original room source.
"""
from pathlib import Path
import sys,struct,mmap,io,json,collections,hashlib,shutil,math,re,subprocess,os,time
import numpy as np
from PIL import Image
from rx3 import Rx3,FORMAT,VERTEX,INDEX,MESH,NAME,TEXTURE,align,sized
ROOT=portable.ROOM
GAME=portable.GAME;LIVE=GAME/'data/sceneassets/server16_dressing_room_20261022'
SOURCE=portable.ROOM/"assets/room.scene"
EXTRACT=None
DTYPE=np.dtype({'names':['p','uv','n'],'formats':[('<f4',3),('<f4',2),('<f4',3)],'offsets':[0,12,44],'itemsize':56})
def packed(v):
 q=np.rint(np.clip(v,-1,1)*511).astype(np.int32)&1023
 return (q[:,0]|(q[:,1]<<10)|(q[:,2]<<20)).astype('<u4')
def prop_file(batches,path):
 template=Rx3((ROOT/'runtime/prop_102.rx3').read_bytes());vbs=[];ibs=[];names=[]
 for i,(vertices,indices) in enumerate(batches):
  p=vertices['p'].astype(np.float32);normal=vertices['n'].astype(np.float32)
  normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8)
  uv=vertices['uv'].astype(np.float32);ids=indices.reshape(-1,3).copy()
  sign=np.einsum('ij,ij->i',np.cross(p[ids[:,1]]-p[ids[:,0]],p[ids[:,2]]-p[ids[:,0]]),normal[ids].mean(axis=1));neg=sign<-.00001;ids[neg]=ids[neg][:,[0,2,1]]
  a,b,c=ids.T;e1=p[b]-p[a];e2=p[c]-p[a];d1=uv[b]-uv[a];d2=uv[c]-uv[a]
  det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0];safe=np.where(np.abs(det)>1e-10,det,1)
  tangent=(e1*d2[:,1,None]-e2*d1[:,1,None])/safe[:,None];tangent[np.abs(det)<=1e-10]=0;acc=np.zeros_like(p)
  for k in range(3):np.add.at(acc,ids[:,k],tangent)
  acc-=normal*np.sum(acc*normal,axis=1,keepdims=True);bad=np.linalg.norm(acc,axis=1)<1e-8
  axis=np.zeros_like(p);axis[:,0]=1;axis[np.abs(normal[:,0])>.9]=[0,0,1];acc[bad]=np.cross(axis[bad],normal[bad]);acc/=np.maximum(np.linalg.norm(acc,axis=1,keepdims=True),1e-8)
  out=np.zeros(len(p),dtype=[('p','<f2',4),('n','<u4'),('g','<u4'),('uv','<f2',2)])
  out['p'][:,:3]=p;out['p'][:,3]=1;out['n']=packed(normal);out['g']=packed(acc);out['uv']=uv
  vb=bytearray(align(16+out.nbytes));struct.pack_into('<4I',vb,0,len(vb),len(p),20,1);vb[16:16+out.nbytes]=out.tobytes();vbs.append(bytes(vb))
  ids=ids.reshape(-1);assert ids.max()<65536
  ib=bytearray(align(16+len(ids)*2));struct.pack_into('<4I',ib,0,len(ib),len(ids),2,0);ib[16:16+len(ids)*2]=ids.astype('<u2').tobytes();ibs.append(bytes(ib));names.append((MESH,f'room_part_{i+1}.FxRenderableSimple'))
 meta=struct.pack('<4I',len(vbs),0,0,0)+b''.join(x[:16] for x in ibs)
 template.sections=[[0x22b2be36,meta,0]]+[[FORMAT,template.get(FORMAT)[0],0] for _ in vbs]+[[NAME,template.get(NAME)[0],0]]+[[INDEX,x,0] for x in ibs]+[[VERTEX,x,0] for x in vbs]+[[MESH,struct.pack('<4I',4,0,0,0),0] for _ in vbs]
 template.set_names(names);path.write_bytes(template.build());shutil.copy2(path,LIVE/path.name)
def scene_parts():
 f=SOURCE.open('rb');data=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);at=8
 stride,club,crest=struct.unpack_from('<I2i',data,at);at+=12+24;np_,nt=struct.unpack_from('<2I',data,at);at+=8;textures=[]
 for _ in range(nt):
  w,h,kind,size=struct.unpack_from('<4I',data,at);at+=16;textures.append((w,h,kind,at,size));at+=size
 def string():
  nonlocal at
  n=struct.unpack_from('<I',data,at)[0];at+=4;s=data[at:at+n].decode('utf8');at+=n;return s
 rows=[]
 for _ in range(np_):
  name,asset=string(),string();tex,coeff=struct.unpack_from('<2i',data,at);at+=8;color=struct.unpack_from('<3f',data,at);at+=12;tint=struct.unpack_from('<3f',data,at);at+=12;blend,alpha=struct.unpack_from('<If',data,at);at+=8
  nv=struct.unpack_from('<I',data,at)[0];at+=4;v=np.frombuffer(data,offset=at,count=nv,dtype=DTYPE).copy();at+=nv*56
  ni=struct.unpack_from('<I',data,at)[0];at+=4;idx=np.frombuffer(data,offset=at,count=ni,dtype='<u4').copy();at+=ni*4
  rows.append(dict(name=name,asset=asset,tex=tex,color=tuple(float(a*b) for a,b in zip(color,tint)),blend=bool(blend),alpha=alpha,v=v,idx=idx))
 def decode(i):
  if i<0:return Image.new('RGBA',(4,4),(255,255,255,255))
  w,h,kind,start,size=textures[i];raw=bytes(data[start:start+size])
  if kind==3:return Image.frombytes('RGBA',(w,h),raw)
  hdr=bytearray(128);hdr[:4]=b'DDS ';struct.pack_into('<7I',hdr,4,124,0x81007,h,w,len(raw),0,1);struct.pack_into('<2I',hdr,76,32,4);hdr[84:88]={0:b'DXT1',1:b'DXT3',2:b'DXT5'}[kind];struct.pack_into('<I',hdr,108,0x1000)
  return Image.open(io.BytesIO(hdr+raw)).convert('RGBA')
 return rows,decode
def static_scene():
 rows,decode=scene_parts();custom=[];crests=[];removed=[];keys={}
 for p in rows:
  native='/native/' in p['asset'] or p['asset'].startswith('data/') or 'kit-number/' in p['asset']
  plate=p['name'].startswith('Armário') and p['asset'].startswith('studio/room/') and p['tex']>=0 and p['tex']!=1
  if p['tex']==0:crests.append(p);continue
  if native or plate:removed.append(p);continue
  key=(p['tex'],p['color'],p['blend'],p['alpha'])
  if key not in keys:keys[key]=len(keys)
  p['key']=keys[key];custom.append(p)
 pages=[Image.new('RGBA',(2048,2048),(255,255,255,255)) for _ in range((len(keys)+63)//64)]
 for (tex,color,blend,alpha),i in keys.items():
  pix=np.array(decode(tex).resize((248,248),Image.Resampling.LANCZOS));pix[:,:,:3]=np.clip(pix[:,:,:3].astype(np.float32)*np.array(color),0,255).astype('uint8');pix[:,:,3]=(np.clip(pix[:,:,3].astype(np.float32)*alpha,0,255).astype('uint8') if blend else 255)
  im=Image.fromarray(pix);pad=im.resize((256,256),Image.Resampling.NEAREST);pad.paste(im,(4,4));pages[i//64].paste(pad,((i%8)*256,(i%64//8)*256))
 for i,im in enumerate(pages):
  p=ROOT/f'assets/scenery_color_{i}.dds';im.save(p,format='DDS',pixel_format='DXT5');shutil.copy2(p,LIVE/p.name)
 groups=collections.defaultdict(list)
 for p in custom:
  v=p['v'];i=p['key'];uv=v['uv'];uv=np.where((uv>=0)&(uv<=1),uv,np.mod(uv,1));uv[:,0]=((i%8)*256+4+uv[:,0]*248)/2048;uv[:,1]=((i%64//8)*256+4+uv[:,1]*248)/2048;v['uv']=uv;v['p'][:,1]+=1000;groups[(i//64,p['blend'])].append((v,p['idx']))
 batches=[];bindings=[]
 for mat,items in groups.items():
  vs=[];ids=[];n=0
  for v,idx in items:
   if n+len(v)>58000:
    batches.append((np.concatenate(vs),np.concatenate(ids)));bindings.append(mat);vs=[];ids=[];n=0
   vs.append(v);ids.append(idx+n);n+=len(v)
  if vs:batches.append((np.concatenate(vs),np.concatenate(ids)));bindings.append(mat)
 prop_file(batches,ROOT/'assets/scenery_only.rx3')
 vs=[];ids=[];n=0
 for p in crests:
  v=p['v'];v['p'][:,1]+=1000;vs.append(v);ids.append(p['idx']+n);n+=len(v)
 assert n<65536
 prop_file([(np.concatenate(vs),np.concatenate(ids))],ROOT/'assets/crest_surfaces.rx3')
 quad=np.zeros(4,dtype=DTYPE);quad['p']=[[-.5,0,0],[.5,0,0],[.5,-1,0],[-.5,-1,0]];quad['uv']=[[0,0],[1,0],[1,1],[0,1]];quad['n']=[0,0,1]
 prop_file([(quad,np.array([0,1,2,0,2,3],dtype='<u4'))],ROOT/'assets/print_surface.rx3')
 manifest={'bindings':bindings,'pages':len(pages),'custom_parts':len(custom),'removed_native_parts':len(removed),'crest_surfaces':len(crests),'static_texture_bytes':sum((ROOT/f'assets/scenery_color_{i}.dds').stat().st_size for i in range(len(pages))),'native_texture_bytes_in_package':0}
 (ROOT/'runtime/scenery_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
if __name__=='__main__':static_scene()
