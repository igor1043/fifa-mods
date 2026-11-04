"""Native material assets: readable sign level, full mips on other materials."""
from pathlib import Path
import tempfile,unittest,struct,hashlib
import numpy as np
from PIL import Image
from rx3 import Rx3,TEXTURE
from room_native_hanging_20261022 import texture_package
from room_texture_tools import color_image
from room_sign_material import ensure


class SignMaterialTests(unittest.TestCase):
    def test_only_opted_in_textures_omit_low_resolution_levels(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);image=Image.new('RGBA',(128,32),(245,245,240,255))
            native=root/'native.rx3';sign=root/'sign.rx3'
            texture_package(image,native,'map');texture_package(image,sign,'map',mipmaps=False)
            normal=Rx3(native.read_bytes()).get(TEXTURE)[0];raw=Rx3(sign.read_bytes()).get(TEXTURE)[0]
            self.assertEqual(struct.unpack_from('<4H',normal,8),(128,32,1,8))
            self.assertEqual(struct.unpack_from('<4H',raw,8),(128,32,1,1))
            pitch,rows,size,_=struct.unpack_from('<4I',raw,16)
            self.assertEqual(len(raw),32+size);self.assertEqual(size,pitch*rows)
            self.assertEqual(normal[32:32+size],raw[32:32+size])

    def test_flat_native_normals_and_matte_coefficient_are_a_separate_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/ensure(root);before=path.read_bytes();ensure(root)
            self.assertEqual(path.read_bytes(),before)
            rx=Rx3(before);self.assertEqual(rx.names(),[(TEXTURE,'_nm'),(TEXTURE,'_coeff')])
            normal=np.asarray(color_image(before,'_nm'));coeff=np.asarray(color_image(before,'_coeff'))
            self.assertTrue(np.all(abs(normal[:,:,:3].astype(int)-[128,128,255])<=4))
            self.assertTrue(np.all(coeff[:,:,:3]<=4))

if __name__=='__main__':unittest.main()
