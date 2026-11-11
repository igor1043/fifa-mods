"""Pack six rendered room faces into an isolated native FIFA reflection asset."""
from pathlib import Path
import io,struct
from PIL import Image,ImageFilter,ImageOps
from . import assets

FACE_ORDER=('px','nx','py','ny','pz','nz')

def cube(faces,blur=0):
    size=faces[0].width
    if size not in (64,128,256,512) or any(p.size!=(size,size) for p in faces):
        raise ValueError('Six square, equally sized power-of-two room faces required')
    if len(faces)!=6:raise ValueError('Six cube faces required')
    mips=size.bit_length();raw=bytearray(16)
    raw[4:8]=bytes((3,2,1,0)) # native cube / BC3 / original texture flags
    struct.pack_into('<4H',raw,8,size,size,6,mips)
    for source in faces:
        image=source.convert('RGBA')
        if blur:image=image.filter(ImageFilter.GaussianBlur(blur))
        while True:
            stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5')
            pixels=stream.getvalue()[128:];pitch=max(1,(image.width+3)//4)*16
            rows=max(1,(image.height+3)//4)
            assert len(pixels)==pitch*rows
            raw.extend(struct.pack('<4I',pitch,rows,len(pixels),0));raw.extend(pixels)
            if image.size==(1,1):break
            image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    struct.pack_into('<I',raw,0,len(raw));return bytes(raw)

def build(template,folder,target):
    rx=assets.Rx3(Path(template).read_bytes());faces=[]
    for name in FACE_ORDER:
        with Image.open(Path(folder)/(name+'.png')) as image:
            # Blender's right-handed face cameras are reflected into Direct3D's
            # cube sampling convention. Geometry and the original cups stay intact.
            faces.append(ImageOps.mirror(image.convert('RGBA')))
    named=[name for typ,name in rx.names() if typ==assets.TEXTURE]
    textures=rx.get(assets.TEXTURE)
    if len(textures)!=len(named):raise ValueError('Native cube directory mismatch')
    if sum(name.startswith(('envs_','envd_')) for name in named)!=2:
        raise ValueError('Native specular/diffuse cube pair required')
    # Do not carry unused stadium reflection pictures into the room asset.
    rx.sections=[section for section in rx.sections if section[0]!=assets.TEXTURE]
    result=['room_diffuse','room_specular']
    rx.sections.extend([[assets.TEXTURE,cube(faces,blur),0] for blur in (20,0)])
    headers=b''.join(p[:16] for p in rx.get(assets.TEXTURE))
    for section in rx.sections:
        if section[0]==0x6bd085dc:section[1]=struct.pack('<4I',2,0,0,0)+headers
    rx.set_names([(assets.TEXTURE,name) for name in result])
    assets.atomic(target,rx.build());return Path(target)
