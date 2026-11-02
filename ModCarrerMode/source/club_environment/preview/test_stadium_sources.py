import io,struct,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from preview_art import stadium_art,stadium_source

class StadiumSources(unittest.TestCase):
 def test_central_converted_dds_and_render_digit_suffix(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);art=root/'data/ui/imgAssets/stadium';art.mkdir(parents=True)
   target=art/'stadium_Arena.dds';Image.new('RGBA',(128,64),'red').save(target,format='DDS',pixel_format='DXT5')
   self.assertEqual(stadium_source(root,'Arena5')[0],str(target))
   result=stadium_art(root,'Arena5','Other',root/'cache');raw=result.read_bytes()
   self.assertEqual(struct.unpack_from('<II',raw,12),(1024,2048))
   self.assertEqual(len(raw),128+2048*1024)
   self.assertEqual(raw[84:88],b'DXT5');self.assertEqual(Image.open(result).getpixel((10,10))[:3],(255,0,0))
 def test_dds_bmp_and_jpeg_are_read_without_guessing_other_stadiums(self):
  for ext in ('.dds','.bmp','.jpg','.png'):
   with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);art=root/'StadiumGBD/render/thumbnail/stadium';art.mkdir(parents=True)
    path=art/('Exact'+ext);Image.new('RGB',(128,64),'blue').save(path)
    self.assertEqual(stadium_source(root,'Exact')[0],str(path))
    self.assertIsNone(stadium_source(root,'Different','Exact'))
    self.assertIsNone(stadium_source(root,'../Exact'))
 def test_photo_crop_and_native_placement_cover_the_complete_card_for_different_aspects(self):
  from unittest.mock import patch
  import build_preview as screen
  from test_preview_summary import MatchSummaryTests
  from formats import AptFile,BigFile,Placement
  for size in ((1600,900),(800,800),(600,1000)):
   with self.subTest(size=size),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);art=root/'StadiumGBD/render/thumbnail/stadium';art.mkdir(parents=True)
    source=Image.new('RGB',size,'#207020');draw=ImageDraw.Draw(source)
    draw.rectangle((0,size[1]//3,size[0]-1,2*size[1]//3),fill='#e06020');source.save(art/'Exact.png')
    encoded=stadium_art(root,'Exact','Exact',root/'cache');photo=Image.open(encoded)
    self.assertEqual(photo.size,(2048,1024));self.assertEqual(photo.getpixel((2047,512))[:3],photo.getpixel((1024,512))[:3])
    payload=MatchSummaryTests().payload();payload['details']['stadium_image_key']='Exact'
    with patch.object(screen,'HERE',root),patch('preview_art.stadium_source',return_value=(str(art/'Exact.png'),(art/'Exact.png').read_bytes())):
     path=screen.build(payload)
    apt=AptFile(BigFile(path));venue=next(p for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name=='venuePage')
    node=next(p for p in apt.characters[venue.character].frames[0] if isinstance(p,Placement) and p.name=='stadiumPhotoArt')
    placement=next(p for p in apt.characters[node.character].frames[0] if isinstance(p,Placement) and p.name=='stadiumPhoto')
    self.assertAlmostEqual(placement.matrix[0]*2048,1050);self.assertAlmostEqual(placement.matrix[3]*1024,404)

if __name__=='__main__':unittest.main()
