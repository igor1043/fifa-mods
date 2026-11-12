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
VERSION='r71'

def native_texture_image(image):
 image=image.convert('RGBA')
 size=tuple(max(4,(dimension+3)//4*4) for dimension in image.size)
 return image if size==image.size else image.resize(size,Image.Resampling.LANCZOS)

def texture_package(image,path,name,*,mipmaps=True,opaque=False):
 """Native mipmap directory, with BC1 available only for proven opaque art."""
 image=native_texture_image(image)
 if opaque and image.getextrema()[3]!=(255,255):raise ValueError('BC1 office art must be fully opaque')
 codec='DXT1' if opaque else 'DXT5';block=8 if opaque else 16
 w,h=image.size;rx=Rx3(TEMPLATE.read_bytes());head=rx.get(TEXTURE)[0][:16];raw=bytearray(head);raw[5]=0 if opaque else 2;mips=0
 while True:
  out=io.BytesIO();image.save(out,format='DDS',pixel_format=codec);dds=out.getvalue();assert dds[84:88]==codec.encode()
  pixels=dds[128:];pitch=max(1,(image.width+3)//4)*block;rows=max(1,(image.height+3)//4);assert len(pixels)==pitch*rows
  raw.extend(struct.pack('<4I',pitch,rows,len(pixels),0));raw.extend(pixels);mips+=1
  if not mipmaps or image.width==image.height==1:break
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
  return max(ys)-3.6
 apex=min(top(0),187.0);left,right=min(top(-19),apex-6),min(top(19),apex-6)
 z=surface(points,ids,0,apex-2);z=42 if z is None else z-1.7
 rows=[];indices=[]
 def tube(a,b,r,metal=False,sides=12):
  a,b=np.array(a),np.array(b);direction=b-a;direction/=np.linalg.norm(direction);axis=np.array([1.,0,0]) if abs(direction[0])<.8 else np.array([0.,0,1]);u=np.cross(direction,axis);u/=np.linalg.norm(u);v=np.cross(direction,u);start=len(rows)
  for p in (a,b):
   for i in range(sides):
    n=u*math.cos(i*2*math.pi/sides)+v*math.sin(i*2*math.pi/sides);rows.append((p+n*r,(.75 if metal else .25,.5),n))
  for i in range(sides):
   j=(i+1)%sides;indices.extend(start+k for k in (i,j,sides+j,i,sides+j,sides+i))
 # Seat every black arm inside the actual cloth volume. Sampling both
 # cloth surfaces avoids a fixed Z plane protruding through either shoulder.
 def inside_z(x,y):
  vv=points[ids.reshape(-1,3)];aa,bb,cc=vv[:,0],vv[:,1],vv[:,2]
  den=(bb[:,1]-cc[:,1])*(aa[:,0]-cc[:,0])+(cc[:,0]-bb[:,0])*(aa[:,1]-cc[:,1])
  safe=np.abs(den)>1e-7
  A=np.divide((bb[:,1]-cc[:,1])*(x-cc[:,0])+(cc[:,0]-bb[:,0])*(y-cc[:,1]),den,out=np.zeros_like(den),where=safe)
  B=np.divide((cc[:,1]-aa[:,1])*(x-cc[:,0])+(aa[:,0]-cc[:,0])*(y-cc[:,1]),den,out=np.zeros_like(den),where=safe);C=1-A-B
  good=safe&(A>=-1e-4)&(B>=-1e-4)&(C>=-1e-4)
  depth=(A*aa[:,2]+B*bb[:,2]+C*cc[:,2])[good]
  return float((depth.min()+depth.max())*.5) if len(depth) else z
 for a,b in [((-19,left),(0,apex)),((0,apex),(19,right)),((-19,min(left,right)-1),(19,min(left,right)-1))]:
  for t in range(24):
   x0,y0=np.array(a)+(np.array(b)-a)*t/24;x1,y1=np.array(a)+(np.array(b)-a)*(t+1)/24
   tube([x0,y0,inside_z(x0,y0)],[x1,y1,inside_z(x1,y1)],.42,sides=8)
 z=inside_z(0,apex)
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
 if path.exists():return 'data/sceneassets/server16_dressing_room_v3/shared/'+filename
 groups=[(shirt,ids),hanger(shirt,ids),decal(shirt,ids,0,192,44,8),decal(shirt,ids,0,180,16,33),decal(shirt,ids,-7,180,13,33),decal(shirt,ids,7,180,13,33)]
 if not path.exists():scene.prop_file(groups,R/'assets'/filename)
 return 'data/sceneassets/server16_dressing_room_v3/shared/'+filename

def hardware_texture():
 p=LIVE/f'hanging_hardware_{VERSION}.rx3'
 if not p.exists():
  im=Image.new('RGBA',(16,8),(18,22,25,255));im.paste((130,139,145,255),(8,0,16,8));texture_package(im,p,'hardware_cm')
 return 'data/sceneassets/server16_dressing_room_v3/shared/'+p.name
