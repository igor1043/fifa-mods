from pathlib import Path
import tempfile,struct,unittest
from PIL import Image
from rx3 import Rx3,TEXTURE
from room_native_hanging_20261022 import native_texture_image,texture_package
from room_texture_tools import color_image

class NativeTextures(unittest.TestCase):
    def test_odd_custom_art_has_valid_bc_dimensions_and_preserves_alpha(self):
        image=Image.new('RGBA',(887,1774),(17,40,80,255))
        self.assertEqual(native_texture_image(image).size,(888,1776))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'corner.rx3';texture_package(image,p,'v3_cm')
            rx=Rx3(p.read_bytes());width,height,depth,mips=struct.unpack_from('<4H',rx.get(TEXTURE)[0],8)
            self.assertEqual((width,height,depth),(888,1776,1));self.assertGreater(mips,1)
            decoded=color_image(p.read_bytes(),'v3_cm')
            self.assertEqual(decoded.size,(888,1776));self.assertEqual(decoded.getextrema()[3],(255,255))
    def test_transparent_art_stays_transparent_and_aligned_art_is_unchanged(self):
        image=Image.new('RGBA',(768,1536),(1,2,3,0))
        self.assertEqual(native_texture_image(image).tobytes(),image.tobytes())
        small=Image.new('RGBA',(5,9),(1,2,3,0))
        self.assertEqual(native_texture_image(small).getextrema()[3],(0,0))
if __name__=='__main__':unittest.main()
