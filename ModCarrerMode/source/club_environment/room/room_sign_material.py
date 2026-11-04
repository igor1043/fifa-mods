"""Small native auxiliary maps for matte printed dressing-room signs."""
from pathlib import Path
import struct,tempfile
from PIL import Image
from rx3 import Rx3,TEXTURE
from room_native_hanging_20261022 import texture_package

PATH='data/sceneassets/server16_dressing_room_v3/sign_aux_v1.rx3'


def ensure(game):
    target=Path(game)/PATH
    if target.is_file():return PATH
    with tempfile.TemporaryDirectory(prefix='room-sign-material-') as folder:
        root=Path(folder);maps=[];rx=None
        for name,rgba in (('_nm',(128,128,255,255)),('_coeff',(0,0,0,255))):
            file=root/(name+'.rx3');texture_package(Image.new('RGBA',(4,4),rgba),file,name)
            part=Rx3(file.read_bytes());maps.append(part.get(TEXTURE)[0])
            if rx is None:rx=part
        rx.sections=[s for s in rx.sections if s[0]!=TEXTURE]
        rx.sections.extend([TEXTURE,raw,0] for raw in maps)
        for section in rx.sections:
            if section[0]==0x6bd085dc:section[1]=struct.pack('<4I',len(maps),0,0,0)+b''.join(raw[:16] for raw in maps)
        rx.set_names([(TEXTURE,'_nm'),(TEXTURE,'_coeff')]);payload=rx.build()
    target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.tmp')
    temporary.write_bytes(payload);temporary.replace(target)
    return PATH
