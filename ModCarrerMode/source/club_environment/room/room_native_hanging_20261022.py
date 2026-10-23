import portable_paths as portable
"""Native jersey pose cache and mesh-following print surfaces, local experiment."""
from pathlib import Path
import sys,json,mmap,struct,math,hashlib,io
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
import room_scene_native_assets_20261022 as scene
from rx3 import Rx3,TEXTURE,read_model
R=scene.ROOT;LIVE=scene.LIVE
TEMPLATE=portable.ROOM/"assets/texture_template.rx3"
VERSION='r50'

def texture_package(image,path,name):
 """Same RX3/DXT5/mipmap directory contract as the working entrance package."""
 image=image.convert('RGBA');w,h=image.size;rx=Rx3(TEMPLATE.read_bytes());head=rx.get(TEXTURE)[0][:16];raw=bytearray(head);raw[5]=2;mips=0
 while True:
  out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT5');dds=out.getvalue();assert dds[84:88]==b'DXT5'
  pixels=dds[128:];pitch=max(1,(image.width+3)//4)*16;rows=max(1,(image.height+3)//4);assert len(pixels)==pitch*rows
  raw.extend(struct.pack('<4I',pitch,rows,len(pixels),0));raw.extend(pixels);mips+=1
  if image.width==image.height==1:break
  image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
 struct.pack_into('<I',raw,0,len(raw));struct.pack_into('<4H',raw,8,w,h,1,mips)
 rx.sections=[s for s in rx.sections if s[0]!=TEXTURE];rx.sections.append([TEXTURE,bytes(raw),0])
 for sec in rx.sections:
  if sec[0]==0x6bd085dc:sec[1]=struct.pack('<4I',1,0,0,0)+raw[:16]
 rx.set_names([(TEXTURE,name)]);payload=rx.build()
 if not path.exists():
  temp=path.with_suffix('.tmp');temp.write_bytes(payload);temp.replace(path)
 return path

def source_shirt(kind):
 native='jersey_0_'+('0' if kind==2 else '8')+'_0_0_1_0_0.rx3'
 with np.load(R/f'assets/jersey_pose_{kind}.npz',allow_pickle=False) as cache:
  v=np.zeros(len(cache['p']),dtype=scene.DTYPE);v['p']=cache['p'];v['uv']=cache['uv'];v['n']=cache['n'];ids=cache['indices'].copy()
 return v,ids,native

def surface(vertices,indices,x,y):
 tri=vertices[indices.reshape(-1,3)];a,b,c=tri[:,0],tri[:,1],tri[:,2]
 den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);safe=np.abs(den)>1e-7
 A=np.divide((b[:,1]-c[:,1])*(x-c[:,0])+(c[:,0]-b[:,0])*(y-c[:,1]),den,out=np.zeros_like(den),where=safe)
 B=np.divide((c[:,1]-a[:,1])*(x-c[:,0])+(a[:,0]-c[:,0])*(y-c[:,1]),den,out=np.zeros_like(den),where=safe);C=1-A-B
 valid=safe&(A>=-1e-4)&(B>=-1e-4)&(C>=-1e-4)
 if not valid.any():return None
 return float(np.max((A*a[:,2]+B*b[:,2]+C*c[:,2])[valid]))

def decal(shirt,ids,center,top,width,height):
 points=shirt['p'];rows=[];idx=[];nx,ny=12,20
 for y in range(ny):
  for x in range(nx):
   uv=[(x/nx,y/ny),((x+1)/nx,y/ny),((x+1)/nx,(y+1)/ny),(x/nx,(y+1)/ny)]
   quad=[]
   for u,v in uv:
    X=center-width*.5+u*width;Y=top-v*height;z=surface(points,ids,X,Y)
    if z is None:break
    quad.append([X,Y,z+.3])
   if len(quad)!=4:continue
   normal=np.cross(np.array(quad[3])-quad[0],np.array(quad[1])-quad[0]);normal/=max(1e-8,np.linalg.norm(normal))
   if normal[2]<0:normal=-normal
   start=len(rows)
   rows.extend((p,uv[i],normal) for i,p in enumerate(quad));idx.extend(start+i for i in (0,1,2,0,2,3))
 out=np.zeros(len(rows),dtype=scene.DTYPE)
 for i,(p,uv,n) in enumerate(rows):out['p'][i]=p;out['uv'][i]=uv;out['n'][i]=n
 assert len(idx)>0,'Print region must project onto native cloth'
 return out,np.array(idx,dtype='<u4')

def hanger(shirt,ids):
 points=shirt['p'];tri=points[ids.reshape(-1,3)]
 def top(x):
  ys=[]
  for a,b in ((tri[:,0],tri[:,1]),(tri[:,1],tri[:,2]),(tri[:,2],tri[:,0])):
   dx=b[:,0]-a[:,0];good=(np.abs(dx)>1e-6)&(x>=np.minimum(a[:,0],b[:,0]))&(x<=np.maximum(a[:,0],b[:,0]))
   ys.extend((a[good,1]+(x-a[good,0])/dx[good]*(b[good,1]-a[good,1])).tolist())
  return max(ys)-1.2
 apex,left,right=top(0),top(-19),top(19);z=surface(points,ids,0,apex-2);z=42 if z is None else z-1.7
 rows=[];indices=[]
 def tube(a,b,r,metal=False,sides=12):
  a,b=np.array(a),np.array(b);direction=b-a;direction/=np.linalg.norm(direction);axis=np.array([1.,0,0]) if abs(direction[0])<.8 else np.array([0.,0,1]);u=np.cross(direction,axis);u/=np.linalg.norm(u);v=np.cross(direction,u);start=len(rows)
  for p in (a,b):
   for i in range(sides):
    n=u*math.cos(i*2*math.pi/sides)+v*math.sin(i*2*math.pi/sides);rows.append((p+n*r,(.75 if metal else .25,.5),n))
  for i in range(sides):
   j=(i+1)%sides;indices.extend(start+k for k in (i,j,sides+j,i,sides+j,sides+i))
 tube([-19,left,z],[0,apex,z],.65);tube([0,apex,z],[19,right,z],.65);tube([-19,left,z],[19,right,z],.65)
 tube([0,apex,z],[0,206,z],.55,True);tube([0,206,z],[0,211.05,32],.55,True)
 for i in range(28):
  a=-math.pi/2+i*math.pi*1.58/28;b=-math.pi/2+(i+1)*math.pi*1.58/28
  tube([0,213.45+2.4*math.sin(a),32+2.4*math.cos(a)],[0,213.45+2.4*math.sin(b),32+2.4*math.cos(b)],.65,True,8)
 out=np.zeros(len(rows),dtype=scene.DTYPE)
 for i,(p,uv,n) in enumerate(rows):out['p'][i]=p;out['uv'][i]=uv;out['n'][i]=n
 return out,np.array(indices,dtype='<u4')

def prepare_geometry(kind,read_asset):
 filename=f'native_hanging_{kind}_{VERSION}.rx3';path=LIVE/filename
 shirt,ids,native=source_shirt(kind)
 original,_=read_model(Rx3(read_asset('data/sceneassets/body/'+native)))
 assert len(original[0]['positions'])//3==len(shirt) and len(original[0]['indices'])==len(ids),'Pose cache must correspond to native jersey topology'
 assert np.max(np.abs(np.array(original[0]['uvs']).reshape(-1,2)-shirt['uv']))<1e-5,'Native kit UVs must be preserved'
 if path.exists():return 'data/sceneassets/server16_dressing_room_20261022/'+filename
 groups=[(shirt,ids),hanger(shirt,ids),decal(shirt,ids,0,192,44,8),decal(shirt,ids,0,180,16,33),decal(shirt,ids,-7,180,13,33),decal(shirt,ids,7,180,13,33)]
 if not path.exists():scene.prop_file(groups,R/'assets'/filename)
 return 'data/sceneassets/server16_dressing_room_20261022/'+filename

def hardware_texture():
 p=LIVE/f'hanging_hardware_{VERSION}.rx3'
 if not p.exists():
  im=Image.new('RGBA',(16,8),(18,22,25,255));im.paste((130,139,145,255),(8,0,16,8));texture_package(im,p,'hardware_cm')
 return 'data/sceneassets/server16_dressing_room_20261022/'+p.name
