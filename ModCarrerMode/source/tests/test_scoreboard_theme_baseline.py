"""Keep the shipped theme at the real Server16 copy sources, not just data/ui."""
from pathlib import Path
import hashlib,shutil,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'ModCarrerMode/source'),str(ROOT/'ModCarrerMode/source/club_environment/vendor')]
from server16_py.file_tools import copy
from server16_py.asset_runtime import AssetRuntime
from formats import BigFile,AptFile
from apt_actions import Actions

RELATIVE=Path('globalcomponents/globalcomponents.big')
VARIANT=Path('XXX - EI Maxx CN')

class ScoreboardThemeBaselineTests(unittest.TestCase):
 def paths(self):
  return (ROOT/'data/ui/game'/RELATIVE,ROOT/'FSW/ScoreBoard'/RELATIVE,ROOT/'ScoreBoardGBD'/VARIANT/'game'/RELATIVE)
 def test_native_and_both_copy_sources_ship_the_same_integrated_theme(self):
  files=self.paths()
  for p in files:self.assertTrue(p.is_file(),f'Missing release asset: {p}')
  self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),1)
 def test_integrated_theme_keeps_native_actionscript_and_readable_text_style(self):
  apt=AptFile(BigFile(self.paths()[1]));actions=Actions(apt).read_all()
  self.assertFalse(actions.errors)
  self.assertEqual(len(actions.functions),1008)
  self.assertEqual(actions.constants[1002],'COLOR_TEXT_UNHIGHLIGHT')
 def test_bootstrap_and_repeated_scoreboard_assignments_cannot_restore_old_palette(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);expected=self.paths()[0].read_bytes()
   for src,rel in zip(self.paths()[1:],(Path('FSW/ScoreBoard')/RELATIVE,Path('ScoreBoardGBD')/VARIANT/'game'/RELATIVE)):
    dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
   # This is the same copy used by Server16App's bootstrap.
   copy(root/'FSW/ScoreBoard',root/'data/ui/game')
   self.assertEqual((root/'data/ui/game'/RELATIVE).read_bytes(),expected)
   app=SimpleNamespace(exedir=root,Scoredata=root/'data/ui',TVdata=root/'data/ui/game/overlays',ScoreBoard=root/'ScoreBoardGBD',
    TOURROUNDID='1',TOURNAME='7',HID='1043',TVLogo=root/'TVLogo',log=Mock(),_set_display=Mock(),
    module_enabled=lambda name:name=='ScoreBoard',display_value=lambda key:key,
    _show_asset_loading=Mock(),_update_asset_loading=Mock(),_hide_asset_loading=Mock(),
    settings_ini=SimpleNamespace(key_exists=lambda key,section:section=='Scoreboard' and key=='7',read=lambda key,section:VARIANT.name))
   runtime=AssetRuntime(app);runtime.update_audio_overview=Mock()
   for _ in range(3):
    runtime.apply_scoreboard_runtime()
    self.assertEqual((root/'data/ui/game'/RELATIVE).read_bytes(),expected)

if __name__=='__main__':unittest.main()
