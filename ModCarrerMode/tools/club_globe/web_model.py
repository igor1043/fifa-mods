"""Convert the owned native model snapshot into WebGL buffers and textures."""
import io,json,struct,hashlib,os
from pathlib import Path
from PIL import Image
def convert(source,folder):
    data=Path(source).read_bytes();offset=8
    if data[:8]!=b'FF3D0001':raise ValueError('Modelo 3D incompatível')
    def read(fmt):
        nonlocal offset
        value=struct.unpack_from(fmt,data,offset);offset+=struct.calcsize(fmt);return value
    def block(size):
        nonlocal offset
        if size<0 or offset+size>len(data):raise ValueError('Buffer 3D inválido')
        result=data[offset:offset+size];offset+=size;return result
    count,textures=read('<II');folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if count>50000 or textures>10000:raise ValueError('Modelo 3D fora dos limites')
    parts=[];buffer=bytearray();bounds=[float('inf')]*3+[float('-inf')]*3
    for i in range(count):
        vc,ic,texture,blend,alpha,*color=read('<IIii7f')
        vertices=block(vc*32);indices=block(ic*4)
        for vertex in struct.iter_unpack('<8f',vertices):
            for axis in range(3):bounds[axis]=min(bounds[axis],vertex[axis]);bounds[axis+3]=max(bounds[axis+3],vertex[axis])
        parts.append({'vertexOffset':len(buffer),'vertexCount':vc,'indexOffset':len(buffer)+len(vertices),'indexCount':ic,'texture':texture,'blend':bool(blend),'alpha':alpha,'color':color[:3],'tint':color[3:]})
        buffer.extend(vertices);buffer.extend(indices)
    texture_paths=[]
    for i in range(textures):
        width,height,kind,size=read('<4I');pixels=block(size);pool=folder.parent/('textures-'+folder.name.split('-')[0]);pool.mkdir(parents=True,exist_ok=True);os.utime(pool,None);path=pool/(hashlib.sha256(struct.pack('<3I',width,height,kind)+pixels).hexdigest()[:24]+'.png')
        if not pixels or not width or not height:texture_paths.append(None);continue
        if path.is_file():texture_paths.append('../'+pool.name+'/'+path.name);continue
        if kind==3:image=Image.frombytes('RGBA',(width,height),pixels[:width*height*4])
        else:
            header=bytearray(128);header[:4]=b'DDS ';struct.pack_into('<7I',header,4,124,0x81007,height,width,len(pixels),0,1)
            struct.pack_into('<II4s',header,76,32,4,[b'DXT1',b'DXT3',b'DXT5'][kind]);struct.pack_into('<I',header,108,0x1000)
            image=Image.open(io.BytesIO(header+pixels)).convert('RGBA')
        image.save(path,'PNG');texture_paths.append('../'+pool.name+'/'+path.name)
    (folder/'geometry.bin').write_bytes(buffer)
    metadata={'parts':parts,'textures':texture_paths,'bounds':bounds,'buffer':'geometry.bin'}
    if data[offset:offset+8]==b'FFCAM001':
        position_x,position_y,position_z,yaw,pitch,fov=struct.unpack_from('<6f',data,offset+8)
        metadata['camera']={'position':[position_x,position_y,position_z],'yaw':yaw,'pitch':pitch,'fov':fov}
        offset+=32
    if data[offset:offset+8]==b'FFMAT001':
        offset+=8
        material_count=read('<I')[0]
        if material_count!=len(parts):raise ValueError('Materiais 3D incompatíveis')
        for part in parts:
            hair,coefficient=read('<Ii');part['hair']=bool(hair);part['hairCoefficient']=coefficient
    (folder/'model.json').write_text(json.dumps(metadata),encoding='utf-8')
    return folder/'model.json'
