"""Execute the generated APT for the third card, not a duplicate UI model."""
from pathlib import Path
import os,tempfile,unittest
import build_apt as screen
from native_review_vm import open_native

class Navigation(unittest.TestCase):
 def test_three_cards_original_input_legends_and_all_return_routes(self):
  with tempfile.TemporaryDirectory(prefix='Coach APT á ') as temp:
   output=Path(temp)/'clubbrowser.big';screen.build(Path(os.environ['SERVER16_GAME_ROOT']),output)
   vm,view,apt,calls=open_native(output,screen.FULL)
   if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
   def press(code):return vm.invoke(view.get('LocalEventHandler'),view,(code,True))
   def command(name):return any(n=='SendSystemEvent' and list(a)==['Calendar','Server16ClubBrowser',name] for n,a in calls)
   press(2);self.assertEqual(view.get('navPage'),1)
   press(6);self.assertEqual(view.get('hubIndex'),2);press(6);self.assertEqual(view.get('hubIndex'),3);press(5);self.assertEqual(view.get('hubIndex'),2)
   press(2);self.assertEqual(view.get('navPage'),5);self.assertTrue(command('coach'))
   self.assertEqual([x[0] for x in vm.invoke(view.get('getHelpContext'),view)],['BACK','L2R2','LAS_UD','RAS_LR','L1R1'])
   press(11);press(12);press(15);press(16)
   self.assertTrue(all(command(k) for k in ('tab_prev','tab_next','prev','next')))
   press(1);self.assertEqual(view.get('navPage'),1)
   for index,page,cmd in ((1,2,'xi'),(2,3,'roster'),(3,5,'coach'),(4,6,'mascot')):
    button=view.get('scene0').get('action'+str(index));vm.invoke(button.get('onRollOver'),button);self.assertEqual(view.get('hubIndex'),index-1);vm.invoke(button.get('onRelease'),button);self.assertEqual(view.get('navPage'),page);self.assertTrue(command(cmd));press(1);self.assertEqual(view.get('navPage'),1)
   press(1);self.assertEqual(view.get('navPage'),0)

if __name__=='__main__':unittest.main()
