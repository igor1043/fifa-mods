"""Personalize only the generated actor texture, using FIFA's own kit artwork.

Hotspots, digit artwork, fonts and assignment precedence come from the game.
No source kit, save, catalog icon or executable is modified here.
"""
import copy,io,math,re,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from native_assets import decode
from rx3 import Rx3,TEXTURE,NAME

class NumberTextures:
 """Texture-only RX3b reader; do not broaden the geometry RX3 parser."""
 def __init__(self,raw):
  if len(raw)<16 or raw[:4]!=b'RX3b' or len(raw)>1024*1024*1024:raise ValueError('Arquivo de números inválido')
  count=struct.unpack_from('>I',raw,12)[0]
  if not 0<count<=20000 or 16+count*16>len(raw):raise ValueError('Diretório de números inválido')
  self._names=[];self._textures=[]
  for i in range(count):
   typ,offset,size,_=struct.unpack_from('>4I',raw,16+i*16)
   if offset<16+count*16 or size<4 or offset+size>len(raw):raise ValueError('Seção de números inválida')
   data=raw[offset:offset+size]
   if typ==TEXTURE:
    if len(data)<32:raise ValueError('Cabeçalho de número incompleto')
    # Only metadata changes byte order. Native pixels keep their channel
    # layout and compression, including files authored as RX3b on PC.
    header=bytearray(data[:32]);struct.pack_into('<I',header,0,struct.unpack_from('>I',data)[0])
    struct.pack_into('<4H',header,8,*struct.unpack_from('>4H',data,8))
    struct.pack_into('<4I',header,16,*struct.unpack_from('>4I',data,16))
    self._textures.append(bytes(header)+data[32:])
   elif typ==NAME:
    if len(data)<16:raise ValueError('Tabela de nomes incompleta')
    n=struct.unpack_from('>I',data,4)[0];at=16
    if n>30000:raise ValueError('Tabela de nomes muito grande')
    for _ in range(n):
     if at+8>len(data):raise ValueError('Nome de número incompleto')
     entry,length=struct.unpack_from('>II',data,at);at+=8
     if not 0<length<=4096 or at+length>len(data):raise ValueError('Nome de número inválido')
     self._names.append((entry,data[at:at+length].split(b'\0',1)[0].decode('utf8')));at+=length
 def names(self):return self._names
 def get(self,kind):return self._textures if kind==TEXTURE else []

def number_rx3(raw):
 if raw[:8] in (b'chunkzip',b'chunkref') or raw[:2]==b'\x10\xfb':
  from containers import unpack
  raw=unpack(raw)
 return NumberTextures(raw) if raw[:4]==b'RX3b' else Rx3(raw)

def hotspots(rx):
 sections=rx.get(0xf55b1a1a)
 if len(sections)!=1:return {}
 raw=sections[0];at=16;result={}
 def text():
  nonlocal at
  end=raw.index(0,at);s=raw[at:end].decode('ascii');at=end+1;return s
 try:
  for _ in range(raw[5]):
   group=text();count=raw[at];at+=1
   if count>32:raise ValueError('Hotspots inválidos')
   result[group]={}
   for _ in range(count):
    name=text();rect=struct.unpack_from('<4f',raw,at);at+=16
    if not all(math.isfinite(v) and -2<=v<=2 for v in rect):raise ValueError('UV inválida')
    result[group][name]=rect
 except (ValueError,IndexError,struct.error,UnicodeError):return {}
 return result

def stamp(name,font_bytes,color,rect):
 name=' '.join(name.upper().split());font=ImageFont.truetype(io.BytesIO(font_bytes),256);box=font.getbbox(name)
 if not name or box[2]<=box[0] or box[3]<=box[1]:return None
 glyph=Image.new('RGBA',(box[2]-box[0],box[3]-box[1]));ImageDraw.Draw(glyph).text((-box[0],-box[1]),name,font=font,fill=tuple(color)+(255,))
 ratio=abs((rect[2]-rect[0])/(rect[3]-rect[1]));height=128;width=max(4,min(4096,2**math.ceil(math.log2(ratio*height))));out=Image.new('RGBA',(width,height))
 scaled=min(width,max(1,round(glyph.width/glyph.height/ratio*width)));glyph=glyph.resize((scaled,height),Image.Resampling.LANCZOS);out.alpha_composite(glyph,((width-scaled)//2,0));return out

def texture_layout(rx,name):
 """Read a native number mip, including the uncompressed FIFA formats.

 RX3 format 3 is A8R8G8B8 (BGRA bytes), whereas generated actor format 3
 is canonical RGBA. Row padding and lower mips are not part of the decal.
 """
 names=[n for typ,n in rx.names() if typ==TEXTURE];entries=rx.get(TEXTURE)
 if len(names)!=len(entries) or names.count(name)!=1:raise ValueError('Nome de textura de número inválido')
 raw=entries[names.index(name)]
 if len(raw)<32:raise ValueError('Cabeçalho de número incompleto')
 kind=raw[5];w,h=struct.unpack_from('<HH',raw,8)
 if kind not in (0,1,2,3,4,5) or not 0<w<=4096 or not 0<h<=4096:raise ValueError('Formato de número não suportado')
 row_bytes=((w+3)//4)*(8 if kind==0 else 16) if kind<3 else w*{3:4,4:1,5:2}[kind]
 rows=(h+3)//4 if kind<3 else h
 pitch,stored_rows,stored,_=struct.unpack_from('<4I',raw,16)
 if pitch<row_bytes or stored_rows<rows or stored<pitch*(rows-1)+row_bytes or 32+stored>len(raw):
  raise ValueError('Textura de número incompleta')
 return raw,w,h,kind,row_bytes,rows,pitch

def texture_record(rx,name):
 raw,w,h,kind,row_bytes,rows,pitch=texture_layout(rx,name)
 pixels=raw[32:32+row_bytes*rows] if pitch==row_bytes else b''.join(raw[32+y*pitch:32+y*pitch+row_bytes] for y in range(rows))
 if kind<3:return w,h,kind,pixels
 if kind==3:image=Image.frombytes('RGBA',(w,h),pixels,'raw','BGRA')
 elif kind==4:image=Image.frombytes('L',(w,h),pixels).convert('RGBA')
 else:
  la=Image.frombytes('LA',(w,h),pixels);l,a=la.split();image=Image.merge('RGBA',(l,l,l,a))
 return w,h,3,image.tobytes()

def surface(shirt,rect,texture,label):
 """A skinned decal on the original UVs, leaving the jersey texture intact."""
 v=shirt['v'];tri=shirt['idx'].reshape(-1,3);uv=v['uv'][tri];a,b,c=uv[:,0],uv[:,1],uv[:,2]
 den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);good=abs(den)>1e-9
 l,t,r,bottom=rect;nx,ny=16,8;vertices=[];indices=[]
 def project(u,z):
  x=np.divide((b[:,1]-c[:,1])*(u-c[:,0])+(c[:,0]-b[:,0])*(z-c[:,1]),den,out=np.zeros_like(den),where=good)
  y=np.divide((c[:,1]-a[:,1])*(u-c[:,0])+(a[:,0]-c[:,0])*(z-c[:,1]),den,out=np.zeros_like(den),where=good);w=1-x-y;hits=np.flatnonzero(good&(x>=-1e-5)&(y>=-1e-5)&(w>=-1e-5))
  if not len(hits):return None
  i=int(hits[0]);weights=np.array([x[i],y[i],w[i]]);source=v[tri[i]];out=np.zeros((),dtype=v.dtype);out['p']=(source['p']*weights[:,None]).sum(axis=0);normal=(source['n']*weights[:,None]).sum(axis=0);normal/=max(1e-8,np.linalg.norm(normal));out['n']=normal;out['p']+=normal*.08
  bones={}
  for bary,row in zip(weights,source):
   for joint,weight in zip(row['j'],row['w']):
    if weight and bary>0:bones[int(joint)]=bones.get(int(joint),0)+float(bary)*int(weight)
  top=sorted(bones.items(),key=lambda item:-item[1])[:8];total=sum(weight for _,weight in top)
  if total<=0:return None
  for k,(joint,weight) in enumerate(top):out['j'][k]=joint;out['w'][k]=max(1,min(255,round(weight/total*255)))
  return out
 for y in range(ny):
  for x in range(nx):
   coords=((x/nx,y/ny),((x+1)/nx,y/ny),((x+1)/nx,(y+1)/ny),(x/nx,(y+1)/ny));points=[project(l+(r-l)*u,t+(bottom-t)*z) for u,z in coords]
   if any(point is None for point in points):continue
   start=len(vertices)
   for point,(u,z) in zip(points,coords):point['uv']=(u,z);vertices.append(point)
   indices.extend(start+k for k in (0,1,2,0,2,3))
 if not indices:raise ValueError('Impressão fora da UV da camisa')
 return dict(name=label,asset='generated/native-kit-print/'+label,texture=texture,skinned=shirt['skinned'],blend=1,alpha=1.,coeff=-1,color=[1.,1.,1.],tint=[1.,1.,1.],v=np.array(vertices,dtype=v.dtype),idx=np.array(indices,dtype='<u4'))

def personalize(rig,player,read_asset):
 """Return a private rig and a source report; leave the shared rig untouched."""
 from room_native_kit_rules_r46 import rules,number_candidates,name_candidates
 club=player['club'];typ=2 if player['position']=='GOL' else 0;league=player.get('league',0);info=copy.deepcopy(player.get('kit_rules',{}))
 base=dict(font=0,color=0,name_font=0,name_color=[255,255,255],layout=0);base.update(info)
 try:text=read_asset(f'data/fifarna/lua/assignments/teams/team_{club}.lua').decode('utf8',errors='replace')
 except FileNotFoundError:text=''
 assignment=rules(text,club,league,{typ:base})
 try:kit=Rx3(read_asset(f'data/sceneassets/kit/kit_{club}_{typ}_0.rx3'))
 except FileNotFoundError:return rig,dict(applied=False,reason='Kit original indisponível')
 uv=hotspots(kit).get('jersey',{});indices={p['texture'] for p in rig['parts'] if '/jersey_' in p['asset'].replace('\\','/').lower() and p['texture']>=0}
 if not indices:return rig,dict(applied=False,reason='Malha da camisa indisponível')
 font=None;font_path=None
 for path in name_candidates(club,typ,league,assignment['default_league'],base['name_font']):
  try:
   blob=read_asset(path);ImageFont.truetype(io.BytesIO(blob),32);font=blob;font_path=path;break
  except (FileNotFoundError,OSError):continue
 digit_rx=None;digit_names={};number_path=None;number_errors=[]
 for path in number_candidates(club,typ,league,assignment['default_league'],base['font'],base['color']):
  try:
   rx=number_rx3(read_asset(path));names={int(m[1]):n for t,n in rx.names() if t==TEXTURE and (m:=re.search(r'_([0-9])(?:\..*)?$',n))}
   if len(names)==10:
    for name in names.values():texture_layout(rx,name)
    digit_rx=rx;digit_names=names;number_path=path;break
  except FileNotFoundError:continue
  except (ValueError,IndexError,struct.error,OSError) as error:
   number_errors.append(dict(path=path,error=str(error)));continue
 printed=[];out=dict(rig,textures=list(rig['textures']),parts=list(rig['parts']));shirt=next(p for p in rig['parts'] if '/jersey_' in p['asset'].replace('\\','/').lower() and p['texture']>=0)
 def add(image,rect,label):
  texture=len(out['textures']);part=surface(shirt,rect,texture,label);out['textures'].append(image);out['parts'].append(part);printed.append(label)
 name_rect=uv.get('name');name=player.get('jersey_name') or player['name']
 if font and name_rect and abs(name_rect[3]-name_rect[1])>1e-6:
  glyph=stamp(name,font,base['name_color'],name_rect)
  if glyph is not None:add((glyph.width,glyph.height,3,glyph.tobytes()),name_rect,'name')
 number=str(player['number']) if 0<=player['number']<=99 else '';rect=uv.get('numberback')
 if digit_rx and number and rect:
  l,t,r,b=rect;mid=(l+r)/2;q=(r-l)/4;cells=[(mid-q,t,mid+q,b)] if len(number)==1 else [(l,t,mid,b),(mid,t,r,b)]
  for digit,cell in zip(number,cells):add(texture_record(digit_rx,digit_names[int(digit)]),cell,'number_'+digit)
 return out,dict(applied=bool(printed),name='name' in printed,number=any(p.startswith('number_') for p in printed),font=font_path,numbers=number_path,number_fallbacks=number_errors[:8],kit_type=typ,source='separate skinned decals; original jersey and native digit pixels unchanged')
