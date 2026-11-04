"""Read editable PNG/DDS or a named color texture from the game's RX3."""
import io
import struct
from PIL import Image
from rx3 import Rx3,TEXTURE


def color_image(data,name=''):
    if data[:4]!=b'RX3l':
        try:return Image.open(io.BytesIO(data)).convert('RGBA')
        except (OSError,ValueError):pass
    rx=Rx3(data);textures=rx.get(TEXTURE)
    names=[n for kind,n in rx.names() if kind==TEXTURE]
    index=next((i for i,n in enumerate(names) if name and (n==name or n.startswith(name+'.'))),0)
    raw=textures[index];w,h=struct.unpack_from('<2H',raw,8)
    pitch,rows,size,_=struct.unpack_from('<4I',raw,16)
    pixels=raw[32:32+size]
    fourcc={0:b'DXT1',1:b'DXT3',2:b'DXT5'}.get(raw[5])
    if not fourcc:raise ValueError('Unsupported color format in RX3: '+str(raw[5]))
    header=bytearray(128);header[:4]=b'DDS '
    struct.pack_into('<7I',header,4,124,0x81007,h,w,len(pixels),0,1)
    struct.pack_into('<2I',header,76,32,4);header[84:88]=fourcc;struct.pack_into('<I',header,108,0x1000)
    return Image.open(io.BytesIO(header+pixels)).convert('RGBA')
