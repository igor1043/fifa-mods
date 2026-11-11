import room_appearance as art
"""Exercise generated APT events at displayed mouse coordinates, not only callbacks."""
import unittest
from apt_vm import Object
from formats import Placement
from test_room_personalization import open_personalization,commands
from room_pointer_ui import ACTIONS,ACTION_Y

def point(vm,s,x,y,event):
 s.set('_xmouse',x);s.set('_ymouse',y);vm.invoke(s.get(event),s)
def click(vm,s,x,y):
 point(vm,s,x,y,'onMouseDown');point(vm,s,x,y,'onMouseUp')

class RoomPointerTests(unittest.TestCase):
 def test_free_camera_and_roster_clicks_without_native_rollover(self):
  vm,s,calls,_=open_personalization()
  point(vm,s,1600,950,'RoomMouseMove');self.assertEqual(s.get('roomActionFocus'),2)
  click(vm,s,1600,950);self.assertTrue(s.get('freeCameraOpen'))
  before=len(commands(calls));click(vm,s,1100,950);self.assertEqual(len(commands(calls)),before)
  vm.invoke(s.get('CloseFreeCamera'),s)
  click(vm,s,1300,950);self.assertTrue(s.get('roomPlayersOpen'))
  before=len(commands(calls));click(vm,s,1600,950);self.assertEqual(len(commands(calls)),before)
  vm.invoke(s.get('RoomPlayersBack'),s);self.assertFalse(s.get('roomPlayersOpen'))
 def test_personalization_arrows_and_apply_click_once(self):
  vm,s,calls,_=open_personalization();click(vm,s,700,950);self.assertTrue(s.get('settingsOpen'))
  original=s.get('settingIndex0');click(vm,s,1720,352);self.assertNotEqual(s.get('settingIndex0'),original)
  click(vm,s,1130,352);self.assertEqual(s.get('settingIndex0'),original)
  click(vm,s,1720,352);click(vm,s,1600,780);self.assertFalse(s.get('settingsOpen'))
  self.assertEqual(sum(int(wire.split('|')[-2]) in art.DOOR_APPLY_CODES for wire in commands(calls)),1)
 def test_table_group_and_both_finishes_are_clickable(self):
  vm,s,calls,_=open_personalization();click(vm,s,700,950)
  click(vm,s,1730,267);self.assertEqual(s.get('settingsGroup'),1)
  click(vm,s,1720,352);click(vm,s,1720,430)
  self.assertEqual(s.get('settingIndex8'),1);self.assertEqual(s.get('settingIndex9'),1)
  click(vm,s,1130,267);self.assertEqual(s.get('settingsGroup'),0)
  self.assertEqual(s.get('settingIndex8'),1);self.assertEqual(s.get('settingIndex9'),1)
 def test_scenes_and_nested_row_use_clicked_row_without_hover(self):
  vm,s,calls,_=open_personalization();click(vm,s,1100,950);self.assertTrue(s.get('modalOpen'))
  click(vm,s,1350,410);self.assertGreaterEqual(s.get('sceneGroup'),0)
  click(vm,s,1350,345);self.assertFalse(s.get('modalOpen'))
 def test_native_release_and_listener_do_not_duplicate_scene_commands(self):
  for native_first in (False,True):
   vm,s,calls,_=open_personalization();button=s.get('freeButton')
   point(vm,s,1600,950,'onMouseDown');before=len(commands(calls))
   if native_first:vm.invoke(button.get('onRelease'),button)
   point(vm,s,1600,950,'onMouseUp')
   if not native_first:vm.invoke(button.get('onRelease'),button)
   self.assertTrue(s.get('freeCameraOpen'));self.assertEqual(len(commands(calls)),before+1)
 def test_dragging_away_and_empty_space_never_activate_a_card(self):
  vm,s,calls,_=open_personalization();before=len(commands(calls))
  point(vm,s,1300,950,'onMouseDown');point(vm,s,1600,950,'onMouseUp')
  click(vm,s,100,500);self.assertEqual(len(commands(calls)),before)
  self.assertFalse(s.get('roomPlayersOpen'));self.assertFalse(s.get('freeCameraOpen'))
 def test_settings_scroll_and_back_are_mouse_accessible(self):
  vm,s,calls,_=open_personalization();click(vm,s,700,950)
  point(vm,s,1775,600,'onMouseDown');point(vm,s,1775,640,'RoomMouseMove');point(vm,s,1775,640,'onMouseUp')
  self.assertGreater(s.get('settingsOffset'),0);self.assertFalse(s.get('settingsDragging'))
  click(vm,s,1250,780);self.assertFalse(s.get('settingsOpen'))

if __name__=='__main__':unittest.main()
