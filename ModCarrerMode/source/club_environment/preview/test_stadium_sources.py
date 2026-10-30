import io,struct,tempfile,unittest
from pathlib import Path
from PIL import Image
from preview_art import stadium_art,stadium_source

class StadiumSources(unittest.TestCase):
 def test_central_converted_dds_and_render_digit_suffix(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);art=root/'data/ui/imgAssets/stadium';art.mkdir(parents=True)
   target=art/'stadium_Arena.dds';Image.new('RGBA',(128,64),'red').save(target,format='DDS',pixel_format='DXT5')
   self.assertEqual(stadium_source(root,'Arena5')[0],str(target))
   result=stadium_art(root,'Arena5','Other',root/'cache');raw=result.read_bytes()
   self.assertEqual(struct.unpack_from('<II',raw,12),(404,1052))
   self.assertEqual(raw[84:88],b'DXT5');self.assertEqual(Image.open(result).getpixel((10,10))[:3],(255,0,0))
 def test_dds_bmp_and_jpeg_are_read_without_guessing_other_stadiums(self):
  for ext in ('.dds','.bmp','.jpg','.png'):
   with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);art=root/'StadiumGBD/render/thumbnail/stadium';art.mkdir(parents=True)
    path=art/('Exact'+ext);Image.new('RGB',(128,64),'blue').save(path)
    self.assertEqual(stadium_source(root,'Exact')[0],str(path))
    self.assertIsNone(stadium_source(root,'Different','Exact'))
    self.assertIsNone(stadium_source(root,'../Exact'))

if __name__=='__main__':unittest.main()
