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
   help=vm.invoke(view.get('getHelpContext'),view)
   self.assertEqual([v[0] for v in help],['ADVANCE','BACK','L2R2','LAS_UD','LAS_LR','L1R1','OPTION_TOP','RAS_UD'])
   self.assertTrue(any(n=='SetCustomSource' for n,args in calls));self.assertTrue(any(n=='Show' for n,args in calls))
   press(10);self.assertTrue(sent('comp_mode'))
   for code in (5,6,11,12,15,16):
    count=len(calls);press(code);self.assertFalse(any(n=='SendSystemEvent' for n,args in calls[count:]),'Native edges own navigation; do not dispatch twice')
   press(2);self.assertTrue(view.get('expanded'));self.assertTrue(sent('comp_bracket'))
   self.assertEqual([v[0] for v in vm.invoke(view.get('getHelpContext'),view)],['BACK','LAS_LR','L1R1','ADVANCE'])
   press(2);self.assertTrue(sent('comp_center'))
   count=len(calls);press(1);self.assertFalse(view.get('expanded'));self.assertTrue(sent('comp_close'))
   self.assertFalse(any(n=='SendEvent' and list(args)==['Calendar','Back',''] for n,args in calls[count:]))
   press(1);self.assertTrue(any(n=='SendEvent' and list(args)==['Calendar','Back',''] for n,args in calls))
   vm.invoke(view.get('OnExitScreen'),view);self.assertTrue(view.get('exiting'));self.assertTrue(any(n=='DisableCurrentLocalEventHandler' for n,args in calls))

if __name__=='__main__':unittest.main(verbosity=2)
