"""Validate and stage supplied native RX3 managers without rerigging them.

The manifest has source model/texture paths, an assetId, coachId and name.
No installation, contract changes or edits to supplied originals occur here.
Native weights, UV seams, head shape and bind matrices remain authored.
"""
from pathlib import Path
import argparse,hashlib,json,struct,sys,shutil,io
import numpy as np
from PIL import Image

def repair_mips(payload):
 width,height,depth,levels=struct.unpack_from('<4H',payload,8);fmt=payload[5]
 if fmt not in (0,1,2) or not 0<width<=4096 or not 0<height<=4096 or depth!=1 or not 1<=levels<=13:raise ValueError('Invalid texture dimensions')
 output=bytearray(payload[:16]);at=16;previous=None;repairs=0
 for level in range(levels):
  pitch,rows,size,reserved=struct.unpack_from('<4I',payload,at);raw=payload[at+16:at+16+size];block=8 if fmt==0 else 16;expected_pitch=max(1,(width+3)//4)*block;expected_rows=max(1,(height+3)//4)
  if len(raw)!=size:raise ValueError('Truncated compressed mip')
  if (pitch,rows,size)!=(expected_pitch,expected_rows,expected_pitch*expected_rows):
   # Supplied 3072px atlases use 6*6 bytes for the final BC3 mip. BC3
   # requires four complete 4x4 blocks (64 bytes), not 36 bytes. Rebuild
   # just this invalid last level from its valid predecessor.
   if level!=levels-1 or previous is None:raise ValueError('Invalid compressed mip buffer')
   pw,ph,prior=previous;header=bytearray(128);header[:4]=b'DDS ';struct.pack_into('<7I',header,4,124,0x81007,ph,pw,len(prior),0,1);struct.pack_into('<2I',header,76,32,4);header[84:88]=(b'DXT1',b'DXT3',b'DXT5')[fmt];struct.pack_into('<I',header,108,0x1000)
   image=Image.open(io.BytesIO(header+prior)).convert('RGBA').resize((width,height),Image.Resampling.LANCZOS);encoded=io.BytesIO();image.save(encoded,format='DDS',pixel_format=('DXT1','DXT3','DXT5')[fmt]);raw=encoded.getvalue()[128:]
   if len(raw)!=expected_pitch*expected_rows:raise ValueError('Mip encoder size mismatch')
   pitch,rows,size=expected_pitch,expected_rows,len(raw);repairs+=1
  output.extend(struct.pack('<4I',pitch,rows,size,reserved));output.extend(raw);previous=(width,height,raw);at+=16+struct.unpack_from('<I',payload,at+8)[0];width=max(1,width//2);height=max(1,height//2)
 if not 0<=len(payload)-at<16:raise ValueError('Unknown compressed mip extension')
 output.extend(b'\0'*((-len(output))%16));struct.pack_into('<I',output,0,len(output));return bytes(output),repairs

def run(manifest,output,tools):
 sys.path.insert(0,str(tools))
 from rx3 import Rx3,read_model,TEXTURE,VERTEX,INDEX,FORMAT
 output=Path(output);reports=[];identities=set();assets=set()
 for job in json.loads(Path(manifest).read_text(encoding='utf8')):
  asset=job['assetId'];identity=job['coachId']
  if type(asset)!=int or not 1<=asset<=200000 or asset in assets or identity in identities:raise ValueError('Duplicate/invalid identity')
  assets.add(asset);identities.add(identity);source=Path(job['model']);original=source.read_bytes();rx=Rx3(original);parts,bind=read_model(rx)
  if len(parts)!=1 or len(bind)!=31:raise ValueError('Expected a compact native manager with 31 bind bones')
  part=parts[0];xyz=np.array(part['positions']).reshape(-1,3);j=np.array(part['joints']).reshape(-1,4);w=np.array(part['weights']).reshape(-1,4);tri=np.array(part['indices']).reshape(-1,3)
  if not np.isfinite(xyz).all() or not (w.sum(1)==255).all() or j[w>0].max()>=31 or tri.min()<0 or tri.max()>=len(xyz) or len(xyz)>65535:raise ValueError('Invalid native geometry/skin')
  if not 150<np.ptp(xyz[:,1])<210:raise ValueError('Unexpected manager scale')
  palette=rx.get(0x0f3861a2)[0];count=struct.unpack_from('<I',palette,4)[0];order=list(palette[272:272+count]);used=set(j[w>0].tolist())
  if len(palette)!=528 or len(set(order))!=count or not used<=set(order) or any(palette[16+bone]!=slot for slot,bone in enumerate(order)):raise ValueError('Unsafe native bone palette')
  vb=rx.get(VERTEX)[0];ib=rx.get(INDEX)[0];vn,stride=struct.unpack_from('<2I',vb,4);indices,width=struct.unpack_from('<2I',ib,4);instance=rx.get(0x22b2be36)[0]
  if vn!=len(xyz) or len(vb)<16+vn*stride or width!=2 or indices!=tri.size or len(ib)<16+indices*width or struct.unpack_from('<3I',instance,16)!=(struct.unpack_from('<I',ib)[0],indices,width):raise ValueError('Native buffer descriptor mismatch')
  tex=Rx3(Path(job['textures']).read_bytes());textures=tex.get(TEXTURE);before=tex.names();roles=[name.lower().removesuffix('.dds').rsplit('_',1)[-1] for typ,name in before if typ==TEXTURE]
  if len(textures)!=3 or set(roles)!={'cm','nm','coeff'}:raise ValueError('Missing native texture role')
  renamed=[(typ,name.removesuffix('.dds')) for typ,name in before];tex.set_names(renamed)
  table=bytearray(tex.get(0x6bd085dc)[0]);repairs=0;texture_sections=[s for s in tex.sections if s[0]==TEXTURE]
  if struct.unpack_from('<I',table)[0]!=3 or len(table)!=64:raise ValueError('Invalid texture-info table')
  for i,payload in enumerate(textures):
   if table[16+i*16:32+i*16]!=payload[:16]:raise ValueError('Texture-info differs from payload; unsafe GPU allocation')
   corrected,changed=repair_mips(payload);texture_sections[i][1]=corrected;repairs+=changed;table[16+i*16:32+i*16]=corrected[:16]
   base_size=struct.unpack_from('<I',payload,24)[0]
   if payload[32:32+base_size]!=corrected[32:32+base_size]:raise ValueError('Base texture changed')
  next(s for s in tex.sections if s[0]==0x6bd085dc)[1]=bytes(table)
  texture=tex.build();folder=output/f'data/sceneassets/manager_market/{asset}';folder.mkdir(parents=True,exist_ok=True);files={}
  for weather in (0,1):
   for suffix,blob in [('',original),('_textures',texture)]:
    path=folder/f'model_{weather}{suffix}.rx3';path.write_bytes(blob);files[path.name]=hashlib.sha256(blob).hexdigest()
  reports.append(dict(assetId=asset,coachId=identity,name=job['name'],vertices=len(xyz),triangles=len(tri),bones=31,sourceFormat=rx.get(FORMAT)[0][16:].split(b'\0')[0].decode(),authoredGeometryWeightsNormalsUVsBindPreserved=True,textureRolesNormalized=before!=renamed,baseTexturesPreserved=True,repairedFinalMipBuffers=repairs,sourceModelSha256=hashlib.sha256(original).hexdigest(),files=files,runtimeValidated=False))
  print('STAGED_NATIVE_MANAGER',asset,job['name'],flush=True)
 (output/'validation.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return reports

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--tools',required=True,type=Path);a=p.parse_args();run(a.manifest,a.output,a.tools)
