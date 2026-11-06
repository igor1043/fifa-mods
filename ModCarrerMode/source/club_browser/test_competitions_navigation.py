"""Exercise the generated native APT, its HelpManager and expanded return path."""
from pathlib import Path
import os,tempfile,unittest
import build_competitions_apt as screen
from native_review_vm import open_native

class CompetitionsNavigation(unittest.TestCase):
 def test_expanded_cup_keeps_native_help_and_returns_to_overview(self):
  with tempfile.TemporaryDirectory(prefix='Competições FIFA á ') as temp:
   path=Path(temp)/'careercompetitions.big';screen.build(Path(os.environ['SERVER16_GAME_ROOT']),path)
   vm,view,apt,calls=open_native(path,screen.FULL)
   if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
   self.assertTrue(view.get('screenReady'))
   def press(code):return vm.invoke(view.get('LocalEventHandler'),view,(code,True))
   def sent(command):return any(n=='SendSystemEvent' and list(args)==['Calendar','Server16ClubBrowser',command] for n,args in calls)
   self.assertEqual(vm.invoke(view.get('getHelpContext'),view),[],'Native renderer owns contextual hints and visible scrolled hit areas')
   for code in (5,6,10,11,12,15,16,17):
    count=len(calls);press(code);self.assertFalse(any(n=='SendSystemEvent' for n,args in calls[count:]),'Native edges own navigation; do not dispatch twice')
   for _ in range(3):
    press(2);self.assertTrue(sent('comp_activate'))
    press(1);self.assertTrue(sent('comp_back'))
   self.assertFalse(any(n=='SendEvent' and list(args)==['Calendar','Back',''] for n,args in calls),'Owner-thread bridge decides whether Back closes a modal or exits')
   for index in (1,4,5):
    button=view.get('scene0').get('action'+str(index))
    self.assertIsNone(button.get('onRelease'),'Unscrolled APT hit rectangles must not capture native clicks')
   vm.invoke(view.get('OnExitScreen'),view);self.assertTrue(view.get('exiting'));self.assertTrue(any(n=='DisableCurrentLocalEventHandler' for n,args in calls))

if __name__=='__main__':unittest.main(verbosity=2)
