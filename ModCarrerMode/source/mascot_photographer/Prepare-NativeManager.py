"""Build model-matched manager textures; preserve native cm/nm/coeff roles."""
from pathlib import Path
import argparse,sys,json,struct,hashlib,io
from PIL import Image

p=argparse.ArgumentParser()
p.add_argument('--output',required=True);p.add_argument('--tools',required=True)
p.add_argument('--texture-template',required=True);p.add_argument('--basecolor',required=True);p.add_argument('--normal',required=True)
p.add_argument('--club-id',type=int,default=1035);p.add_argument('--coefficient')
a=p.parse_args();root=Path(a.output)
sys.path[:0]=[str(Path(a.tools)),str(Path(a.tools)/'vendor/rx3tools')]
from rx3 import Rx3,TEXTURE,read_model
from texture_assets import rx3_colour_png
rx=Rx3(Path(a.texture_template).read_bytes());sections=[s for s in rx.sections if s[0]==TEXTURE]
names=[name for kind,name in rx.names() if kind==TEXTURE]
if len(sections)!=3 or len(names)!=3:raise ValueError('Expected manager cm/nm/coeff texture set')
def encode(image,header,limit):
    image=image.convert('RGBA');image.thumbnail((limit,limit),Image.Resampling.LANCZOS)
    w,h=image.size
    if w!=h or w&(w-1):raise ValueError('Expected square power-of-two texture')
    data=bytearray(header[:16]);data[5]=2;count=0
    while True:
        stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5');payload=stream.getvalue()[128:]
        pitch=max(1,(image.width+3)//4)*16;rows=max(1,(image.height+3)//4)
        if len(payload)!=pitch*rows:raise ValueError('Invalid DDS block dimensions')
        data.extend(struct.pack('<4I',pitch,rows,len(payload),0));data.extend(payload);count+=1
        if image.width==1:break
        image=image.resize((image.width//2,image.height//2),Image.Resampling.LANCZOS)
    struct.pack_into('<I',data,0,len(data));struct.pack_into('<4H',data,8,w,h,1,count)
    return bytes(data)
maps=[('cm',a.basecolor),('nm',a.normal)]
if a.coefficient:maps.append(('coeff',a.coefficient))
for suffix,path in maps:
    matching=[i for i,name in enumerate(names) if name==suffix or name.endswith('_'+suffix)]
    if len(matching)!=1:raise ValueError('Ambiguous native texture role '+suffix)
    i=matching[0];sections[i][1]=encode(Image.open(path),sections[i][1],2048 if suffix=='cm' else 1024)

# RX3 duplicates each texture's 16-byte header in the texture-info table.
# The engine uses that table when allocating/decoding image buffers. Keeping
# the template's BC1 descriptors after writing BC3 payloads advertises half
# the required storage, even though the per-texture mip headers are correct.
infoSections=[s for s in rx.sections if s[0]==0x6bd085dc]
if len(infoSections)!=1:raise ValueError('Expected one native texture-info table')
info=bytearray(infoSections[0][1]);count=struct.unpack_from('<I',info,0)[0]
if count!=len(sections) or len(info)!=16+count*16:raise ValueError('Unexpected native texture-info layout')
for i,section in enumerate(sections):info[16+i*16:32+i*16]=section[1][:16]
infoSections[0][1]=bytes(info)
dest=root/'package/data/sceneassets/slc';model=dest/f'specificmanager_{a.club_id}_0_0.rx3'
if not model.is_file():raise ValueError('Convert manager model before preparing textures')
texture=dest/f'specificmanager_{a.club_id}_0_0_textures.rx3';texture.write_bytes(rx.build())
written=Rx3(texture.read_bytes());table=written.get(0x6bd085dc)[0]
for i,section in enumerate(written.get(TEXTURE)):
    if table[16+i*16:32+i*16]!=section[:16]:raise ValueError('Texture-info descriptor does not match its payload')
(root/'exported_basecolor.png').write_bytes(rx3_colour_png(texture))
# Both weather fallbacks resolve to this complete club-specific human model.
(dest/f'specificmanager_{a.club_id}_0_1.rx3').write_bytes(model.read_bytes())
(dest/f'specificmanager_{a.club_id}_0_1_textures.rx3').write_bytes(texture.read_bytes())
for s in Rx3(texture.read_bytes()).get(TEXTURE):
    w,h,d,n=struct.unpack_from('<4H',s,8);at=16
    block=8 if s[5]==0 else 16
    for level in range(n):
        pitch,rows,size,_=struct.unpack_from('<4I',s,at)
        assert pitch==max(1,(w+3)//4)*block and rows==max(1,(h+3)//4) and size==pitch*rows
        at+=16+size;w=max(1,w//2);h=max(1,h//2)
    assert 0<=len(s)-at<16
parts,bind=read_model(Rx3(model.read_bytes()))
report=dict(clubId=a.club_id,textureRoles=names,normalMapSlot=next(i for i,n in enumerate(names) if n.endswith('_nm')),textureInfoMatchesPayloads=True,coefficientMapPreserved=not bool(a.coefficient),coefficientMapSource=a.coefficient,modelsUseNativeManagerBind=True,files={f.name:dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in dest.iterdir() if f.is_file()})
(root/'package_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PREPARED NATIVE MANAGER:',len(report['files']),'files; roles',names)
