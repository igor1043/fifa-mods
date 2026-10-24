"""Neutral ambient cubes for the static native XI; generated only on request.

Preserve cube layout, alpha, mipmaps and directional luminance. Remove the
coloured environment reflection from the static-prop material, not from any
player diffuse texture. Original FIFA assets and all save data stay read-only.
"""
from pathlib import Path
import os,struct,io
from PIL import ImageOps
from native_assets import decode
from rx3 import Rx3,TEXTURE

VERSION=2

def neutral_cube(blob):
    rx=Rx3(blob);names=[name for kind,name in rx.names() if kind==TEXTURE]
    entries=rx.get(TEXTURE)
    if len(names)!=len(entries):raise ValueError('Character lighting texture directory')
    count=0
    for name,section in zip(names,entries):
        if not name.startswith(('envd_','envs_')):continue
        data=bytearray(section);width,height,depth,mips=struct.unpack_from('<4H',data,8);kind=data[5]
        if kind!=2 or depth!=6 or not 1<=mips<=12:raise ValueError('Unsupported character lighting cube')
        at=16
        for face in range(depth):
            w,h=width,height
            for level in range(mips):
                pitch,rows,size,reserved=struct.unpack_from('<4I',data,at);at+=16
                if size!=((w+3)//4)*((h+3)//4)*16 or at+size>len(data):raise ValueError('Truncated character lighting cube')
                image=decode((w,h,kind,bytes(data[at:at+size])))
                grey=ImageOps.grayscale(image).convert('RGBA');grey.putalpha(image.getchannel('A'))
                out=io.BytesIO();grey.save(out,format='DDS',pixel_format='DXT5');pixels=bytearray(out.getvalue()[128:])
                if len(pixels)!=size:raise ValueError('Cube mip changed length')
                # BC3 keeps alpha in the first eight bytes of every block.
                # Preserve those compressed bytes exactly, avoiding alpha loss
                # from the RGB-only environment neutralization.
                for block in range(0,size,16):pixels[block:block+8]=data[at+block:at+block+8]
                data[at:at+size]=pixels;at+=size;w,h=max(1,w//2),max(1,h//2)
        rx.sections[next(i for i,s in enumerate(rx.sections) if s[0]==TEXTURE and s[1] is section)][1]=bytes(data);count+=1
    if count!=2:raise ValueError('Diffuse/specular environment maps unavailable')
    return rx.build()

def ensure(game,read_asset):
    folder=Path(game)/'data/sceneassets/server16_club_xi/lighting';folder.mkdir(parents=True,exist_ok=True);written=[]
    for env in (0,1):
        target=folder/f'charcmn_{env}_neutral_v{VERSION}.rx3'
        if target.is_file():
            raw=target.read_bytes()
            if len(raw)>=32 and raw[:4]==b'RX3l' and struct.unpack_from('<I',raw,8)[0]==len(raw):continue
        blob=neutral_cube(read_asset(f'data/sceneassets/charactercmn/charactercmn_{env}.rx3'))
        temp=target.with_name(target.name+'.'+str(os.getpid())+'.new');temp.write_bytes(blob);os.replace(temp,target);written.append(target)
    return written
