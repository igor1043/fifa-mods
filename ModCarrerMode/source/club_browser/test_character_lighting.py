"""Use original FIFA cubes; preserve native cube/mip layout and player pixels."""
import hashlib,struct,sys,tempfile
from pathlib import Path
import numpy as np
from character_lighting import neutral_cube,ensure
from native_assets import decode
from rx3 import Rx3,TEXTURE
import portable_paths

def run():
    for env in (0,1):
        blob=portable_paths.read_asset(f'data/sceneassets/charactercmn/charactercmn_{env}.rx3')
        old=Rx3(blob);new=Rx3(neutral_cube(blob));assert old.names()==new.names()
        names=[name for kind,name in old.names() if kind==TEXTURE]
        for name,a,b in zip(names,old.get(TEXTURE),new.get(TEXTURE)):
            if not name.startswith(('envd_','envs_')):assert a==b;continue
            assert len(a)==len(b) and a[:16]==b[:16]
            w,h,faces,mips=struct.unpack_from('<4H',a,8);at=16
            assert faces==6 and mips==8
            for face in range(faces):
                width,height=w,h
                for mip in range(mips):
                    assert a[at:at+16]==b[at:at+16];size=struct.unpack_from('<I',a,at+8)[0];at+=16
                    source=np.array(decode((width,height,2,a[at:at+size])),dtype='int16')
                    grey=np.array(decode((width,height,2,b[at:at+size])),dtype='int16')
                    assert (np.max(grey[:,:,:3],axis=2)-np.min(grey[:,:,:3],axis=2)).max()<=9
                    assert np.array_equal(source[:,:,3],grey[:,:,3])
                    for block in range(0,size,16):assert a[at+block:at+block+8]==b[at+block:at+block+8]
                    at+=size;width,height=max(1,width//2),max(1,height//2)
        assert hashlib.sha256(blob).digest()==hashlib.sha256(portable_paths.read_asset(f'data/sceneassets/charactercmn/charactercmn_{env}.rx3')).digest()
    with tempfile.TemporaryDirectory(prefix='xi-lighting-test-') as tmp:
        paths=ensure(tmp,portable_paths.read_asset);assert len(paths)==2
        def unexpected(_):raise AssertionError('Valid cache should not read any source')
        assert not ensure(tmp,unexpected)
        paths[0].write_bytes(b'RX3l');assert len(ensure(tmp,portable_paths.read_asset))==1
    print('PASS lighting: 6 cube faces, all mip records, alpha, unrelated textures and original files preserved; neutral RGB and lazy cache verified')

if __name__=='__main__':run()
