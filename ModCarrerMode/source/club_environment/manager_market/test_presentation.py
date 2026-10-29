from pathlib import Path
import io,struct,tempfile,unittest
from unittest.mock import patch
import test_screen
from PIL import Image
from formats import BigFile,chunk_wrap,chunk_unwrap
from screen import scenes_for,stars
from native_screen import block_texture
from asset_cache import prepared,revision,_warm
from club_portraits import portrait

class PresentationTest(unittest.TestCase):
 def test_dxt_block_padding_preserves_every_source_pixel(self):
  src=Image.new('RGBA',(202,202),(195,30,55,255));fixed=block_texture(src)
  self.assertEqual((204,204),fixed.size);self.assertEqual(src.tobytes(),fixed.crop((0,0,202,202)).tobytes());self.assertEqual(0,fixed.getpixel((203,203))[3])
  data=io.BytesIO();fixed.save(data,format='DDS',pixel_format='DXT5');height,width=struct.unpack_from('<II',data.getvalue(),12);self.assertEqual(0,width%4);self.assertEqual(0,height%4)
 def test_package_textures_all_meet_native_dxt_block_constraints(self):
  big=BigFile(test_screen.NativeScreenTest.package)
  textures=[e.data for e in big.entries.values() if e.data.startswith(b'DDS ')]
  self.assertGreater(len(textures),10)
  for blob in textures:
   if blob[84:88] not in (b'DXT1',b'DXT3',b'DXT5'):continue
   height,width=struct.unpack_from('<II',blob,12);self.assertEqual((0,0),(width%4,height%4))
 def test_no_visual_back_buttons_and_selected_tabs_have_gold_artwork(self):
  model=test_screen.NativeScreenTest.model;assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64)),'card':Image.new('RGBA',(8,8)),**{'stars_'+str(n):stars(n) for n in range(11)}};scenes=scenes_for(model,assets)
  self.assertFalse(any(n.get('target')=='60' for s in scenes for n in s['actions']))
  tabs=[n for n in scenes[1]['nodes'] if n.get('name','').startswith('profileMark')];self.assertEqual(4,len(tabs));self.assertTrue(all(n['asset']=='profile_tab_on' for n in tabs));self.assertEqual(128,assets['profile_icon_trophy'].width)
  self.assertFalse(any('CLUBES NESTA LIGA'==n.get('text') for n in scenes[0]['nodes']))
 def test_portrait_corners_use_actual_palette_and_do_not_modify_source(self):
  source=Image.new('RGBA',(128,128));before=source.tobytes();one=portrait(source,('#ef1133','#131313'));two=portrait(source,('#0099cc','#ffffff'))
  self.assertEqual(before,source.tobytes());self.assertEqual((256,256),one.size);self.assertNotEqual(one.getpixel((15,15)),two.getpixel((15,15)))
 def test_cache_survives_service_restart_and_invalidates_changed_head(self):
  with tempfile.TemporaryDirectory() as temp:
   game=Path(temp);head=game/'ModCarrerMode/data/manager_market/minifaces/1.png';head.parent.mkdir(parents=True);head.write_bytes(b'one')
   model=dict(people=[dict(image='minifaces/1.png',head='head_1')],clubRows=[],moveRows=[],hireRows=[],leagues=[],countries=[]);calls=[]
   def factory():calls.append(1);return {'head_1':Image.new('RGBA',(128,128),'red')}
   _warm.clear();key=revision(game,model);prepared(game,model,factory);_warm.clear();loaded=prepared(game,model,factory);self.assertEqual(1,len(calls));self.assertEqual((255,0,0,255),loaded['head_1'].getpixel((0,0)))
   head.write_bytes(b'new photo');self.assertNotEqual(key,revision(game,model));prepared(game,model,factory);self.assertEqual(2,len(calls));_warm.clear()
 def test_fast_compression_preserves_identical_native_container_content(self):
  header=b'chunkzip'+struct.pack('>5I',2,0,65536,0,16)+bytes(12);raw=b'APT data and texture'*10000
  for level in (1,9):self.assertEqual(raw,chunk_unwrap(chunk_wrap(raw,header,level=level))[0])

def setUpModule():test_screen.NativeScreenTest.setUpClass()
def tearDownModule():test_screen.NativeScreenTest.tearDownClass()
