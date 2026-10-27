import portable_paths as portable
"""Preserve room labels/decals at float32 precision using a native RX3 layout."""
from room_scene_native_assets_20261022 import ROOT,LIVE,packed,np,struct,align,shutil,Rx3,FORMAT,VERTEX,INDEX,MESH,NAME
def precise_prop_file(batches,path):
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
  out=np.zeros(len(p),dtype=[('p','<f4',3),('n','<u4'),('g','<u4'),('uv','<f2',2)])
  out['p'][:]=p;out['n']=packed(normal);out['g']=packed(acc);out['uv']=uv
  vb=bytearray(align(16+out.nbytes));struct.pack_into('<4I',vb,0,len(vb),len(p),24,1);vb[16:16+out.nbytes]=out.tobytes();vbs.append(bytes(vb))
  ids=ids.reshape(-1);assert ids.max()<65536
  ib=bytearray(align(16+len(ids)*2));struct.pack_into('<4I',ib,0,len(ib),len(ids),2,0);ib[16:16+len(ids)*2]=ids.astype('<u2').tobytes();ibs.append(bytes(ib));names.append((MESH,f'room_part_{i+1}.FxRenderableSimple'))
 meta=struct.pack('<4I',len(vbs),0,0,0)+b''.join(x[:16] for x in ibs)
 text=b'p0:00:00:0001:3f32 n0:0C:00:0001:3s10n g0:10:00:0001:3s10n t0:14:00:0001:2f16\0';fmt=struct.pack('<4I',align(16+len(text)),len(text),0,0)+text;fmt+=bytes(align(len(fmt))-len(fmt))
 template.sections=[[0x22b2be36,meta,0]]+[[FORMAT,fmt,0] for _ in vbs]+[[NAME,template.get(NAME)[0],0]]+[[INDEX,x,0] for x in ibs]+[[VERTEX,x,0] for x in vbs]+[[MESH,struct.pack('<4I',4,0,0,0),0] for _ in vbs]
 template.set_names(names);path.write_bytes(template.build());shutil.copy2(path,LIVE/path.name)
