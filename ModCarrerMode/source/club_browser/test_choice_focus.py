import os,tempfile,unittest
from pathlib import Path
import build_apt as screen
from native_review_vm import open_native

class ClubChoiceFocus(unittest.TestCase):
 def test_repeated_mouse_keyboard_and_pad_returns_keep_activation_with_highlight(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'browser.big';screen.build(Path(os.environ['SERVER16_GAME_ROOT']),path)
   vm,view,apt,calls=open_native(path,screen.FULL)
   if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
   def press(code):vm.invoke(view.get('LocalEventHandler'),view,(code,True))
   def commands(start):return [args[2] for name,args in calls[start:] if name=='SendSystemEvent' and args[1]=='Server16ClubBrowser']
   press(2);self.assertEqual(view.get('navPage'),1)
   focus=['focus_xi','focus_roster','focus_coach','focus_mascot'];routes=['xi','roster','coach','mascot'];pages=[2,3,5,6]
   for cycle in range(16):
    # Hover chooses one card; keyboard/pad then activates or moves from it.
    index=cycle%4;button=view.get('scene0').get('action'+str(index+1))
    start=len(calls);vm.invoke(button.get('onRollOver'),button)
    self.assertEqual(commands(start),[focus[index]])
    if cycle%2:
     start=len(calls);press(6);index=(index+1)%4
     self.assertEqual(commands(start),[focus[index]])
    self.assertEqual(view.get('hubIndex'),index)
    start=len(calls);press(7 if cycle%2 else 2)
    self.assertEqual(view.get('navPage'),pages[index]);self.assertEqual(commands(start),[focus[index],routes[index]])
    # A stale rollover from hidden choice cards cannot change the next action.
    other=view.get('scene0').get('action'+str((index+1)%4+1));start=len(calls)
    vm.invoke(other.get('onRollOver'),other)
    self.assertEqual(view.get('hubIndex'),index);self.assertEqual(commands(start),[])
    start=len(calls);press(1)
    self.assertEqual(view.get('navPage'),1);self.assertEqual(commands(start),['back',focus[index]])
    # Activate again without moving the mouse: this was the drift scenario.
    start=len(calls);press(2)
    self.assertEqual(view.get('navPage'),pages[index]);self.assertEqual(commands(start)[-1],routes[index])
    press(1)
   # Returning to the globe and opening another club preserves one focus owner.
   press(1);self.assertEqual(view.get('navPage'),0)
   start=len(calls);press(2);self.assertEqual(commands(start),['open',focus[view.get('hubIndex')]])

if __name__=='__main__':unittest.main(verbosity=2)
