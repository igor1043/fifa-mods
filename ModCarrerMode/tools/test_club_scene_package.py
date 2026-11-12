"""Regression for rooms that loaded locally but lost hashed models in the ZIP."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('club_package',Path(__file__).with_name('Build-ClubScenesPackage.py'))
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


class RoomPackageDependencies(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.manifest=self.root/package.ROOM_MODEL_MANIFEST
  self.manifest.parent.mkdir(parents=True)

 def scene(self,document,names):
  self.manifest.write_text(json.dumps(document),encoding='utf8')
  for name in names:(self.manifest.parent/name).write_bytes(b'RX3 fixture')

 def test_frame_and_palette_survive_without_any_previous_installation_cache(self):
  names=['locker_bay_hash.rx3','next_match_board_8a60b707154871.rx3','next_match_board_palette_hash.rx3','exit_door_hash.rx3']
  self.scene({'model_files':{'locker_bay.rx3':names[0],'exit_door.rx3':names[3]},
              'next_match_board':{'model':names[1],'texture':names[2]},
              'exit_door':{'custom_image':'exit-door.png'}},names)
  self.assertEqual({self.manifest,*[self.manifest.parent/n for n in names]},set(package.room_model_assets(self.root)))

 def test_missing_match_board_aborts_packaging_instead_of_publishing_broken_zip(self):
  self.scene({'next_match_board':{'model':'next_match_board_8a60b707154871.rx3'}},[])
  with self.assertRaisesRegex(FileNotFoundError,'next_match_board_8a60b707154871'):
   package.room_model_assets(self.root)

 def test_manifest_cannot_pull_files_from_another_folder(self):
  for value in ('../private.rx3','C:/private.rx3','/private.rx3','data/other/private.rx3'):
   with self.subTest(value=value):
    self.scene({'model':value},[])
    with self.assertRaises(ValueError):package.room_model_assets(self.root)


if __name__=='__main__':unittest.main()
