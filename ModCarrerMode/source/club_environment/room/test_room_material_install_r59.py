import portable_paths as portable
import unittest,hashlib,json,struct
from pathlib import Path
from room_scene_native_assets_20261022 import ROOT,LIVE,Rx3,TEXTURE

class MaterialInstall(unittest.TestCase):
 def test_native_dependencies_are_in_the_game_asset_directory(self):
  for name in ('scenery_r62.rx3','scenery_textures_0_r62.rx3','scenery_textures_1_r62.rx3'):
   self.assertTrue((LIVE/name).is_file(),name)
   self.assertTrue((LIVE/name).read_bytes().startswith(b'RX3l'))
 def test_atlases_have_full_valid_mip_chains_and_the_requested_colour_name(self):
  for i in range(2):
   rx=Rx3((LIVE/f'scenery_textures_{i}_r62.rx3').read_bytes());self.assertIn((TEXTURE,'room_cm'),rx.names());raw=rx.get(TEXTURE)[0];w,h,depth,mips=struct.unpack_from('<4H',raw,8);self.assertEqual((w,h),(2048,2048));at=16
   for level in range(mips):
    pitch,rows,size,_=struct.unpack_from('<4I',raw,at);self.assertEqual(pitch,max(1,(w+3)//4)*16);self.assertEqual(rows,max(1,(h+3)//4));self.assertEqual(size,pitch*rows);at+=16+size;w=max(1,w//2);h=max(1,h//2)
   self.assertEqual(at,len(raw));self.assertEqual((w,h),(1,1))
 def test_approved_light_is_unchanged(self):
  self.assertEqual(hashlib.sha256((portable.SOURCES/'room/native/room_lighting_r46.h').read_bytes()).hexdigest(),'7cb11a4a3241aab8ffa5f6123b639a881c3624dbb92a841fa7e8b4ecb1746c80')
 def test_replacement_module_has_its_own_native_component_types(self):
  source=(portable.SOURCES/'room/native/native_dressing_room_20261022.cpp').read_text(encoding='utf8');components=(portable.SOURCES/'room/native/room_components_native_r46.h').read_text(encoding='utf8')
  self.assertIn('server16_native_dressing_room_r60',source);self.assertIn('server16_native_room_r60_',components)
  self.assertIn('server16_room_loading_r60',components);self.assertIn('server16_room_error_r60',components)
  self.assertNotIn('server16_native_room_r58_',components);self.assertIn('MISSING_INSTALLED_ROOM_ASSET',source)

if __name__=='__main__':unittest.main(verbosity=2)
