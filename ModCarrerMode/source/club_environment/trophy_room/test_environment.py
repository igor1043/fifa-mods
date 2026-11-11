import io,struct,tempfile,unittest
from pathlib import Path
from PIL import Image
import numpy as np
from . import environment,assets

class EnvironmentTests(unittest.TestCase):
    def test_native_cube_contains_all_faces_and_complete_mip_chains(self):
        colors=[(210,30,30),(30,210,30),(30,30,210),(210,210,30),(210,30,210),(30,210,210)]
        raw=environment.cube([Image.new('RGBA',(64,64),(*color,255)) for color in colors])
        self.assertEqual(raw[4:8],bytes((3,2,1,0)))
        self.assertEqual(struct.unpack_from('<4H',raw,8),(64,64,6,7))
        at=16
        for color in colors:
            for level in range(7):
                size=max(1,64>>level);pitch,rows,length,_=struct.unpack_from('<4I',raw,at);at+=16
                self.assertEqual(length,max(1,(size+3)//4)**2*16)
                self.assertEqual((pitch,rows),(max(1,(size+3)//4)*16,max(1,(size+3)//4)))
                if level==0:
                    # DDS uses the same BC3 payload; verify colours after actual
                    # compression/decompression, rather than just header bytes.
                    head=bytearray(128);head[:4]=b'DDS ';struct.pack_into('<I',head,4,124)
                    struct.pack_into('<I',head,12,size);struct.pack_into('<I',head,16,size)
                    struct.pack_into('<I',head,76,32);struct.pack_into('<I',head,80,4);head[84:88]=b'DXT5'
                    image=Image.open(io.BytesIO(bytes(head)+raw[at:at+length])).convert('RGB')
                    self.assertLess(np.max(np.abs(np.asarray(image,dtype=int)[0,0]-color)),12)
                at+=length
        self.assertEqual(at,len(raw))
        self.assertEqual(struct.unpack_from('<I',raw)[0],len(raw))

    def test_rejects_invalid_face_count_and_dimensions(self):
        with self.assertRaises(ValueError):environment.cube([Image.new('RGBA',(64,64))]*5)
        with self.assertRaises(ValueError):environment.cube([Image.new('RGBA',(63,64))]*6)

if __name__=='__main__':unittest.main()
