from pathlib import Path
import tempfile,struct,unittest
import numpy as np
from PIL import Image,ImageDraw
from room_native_hanging_20261022 import texture_package
from room_texture_tools import color_image
from rx3 import Rx3,TEXTURE


class OpaqueMonitorTextures(unittest.TestCase):
    def test_bc1_keeps_resolution_mipmaps_and_rgb_at_half_the_size(self):
        im=Image.new('RGBA',(512,256),(240,242,244,255));d=ImageDraw.Draw(im)
        d.rectangle((0,0,100,255),fill=(14,73,45));d.rectangle((150,80,490,185),fill=(29,40,47))
        with tempfile.TemporaryDirectory() as folder:
            a,b=Path(folder)/'alpha.rx3',Path(folder)/'opaque.rx3'
            texture_package(im,a,'coach_cm');texture_package(im,b,'coach_cm',opaque=True)
            raw=Rx3(b.read_bytes()).get(TEXTURE)[0]
            self.assertEqual(raw[5],0);self.assertEqual(struct.unpack_from('<4H',raw,8),(512,256,1,10))
            self.assertLess(b.stat().st_size,a.stat().st_size*.51)
            bc1=np.asarray(color_image(b.read_bytes(),'coach_cm'));bc3=np.asarray(color_image(a.read_bytes(),'coach_cm'))
            self.assertTrue((bc1[:,:,3]==255).all())
            self.assertLess(np.abs(bc1[:,:,:3].astype(float)-bc3[:,:,:3]).mean(),1.)

    def test_transparent_assets_cannot_enter_the_opaque_path(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):texture_package(Image.new('RGBA',(16,16),(255,0,0,80)),Path(folder)/'no.rx3','coach_cm',opaque=True)

    def test_default_path_retains_bc3_and_alpha_for_all_other_mods(self):
        im=Image.new('RGBA',(16,16),(240,30,20,0));im.paste((20,150,230,255),(0,0,8,16))
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'default.rx3';texture_package(im,p,'texture')
            self.assertEqual(Rx3(p.read_bytes()).get(TEXTURE)[0][5],2)
            alpha=color_image(p.read_bytes(),'texture').getchannel('A')
            self.assertEqual(alpha.getextrema(),(0,255))


if __name__=='__main__':unittest.main()
