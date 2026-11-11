"""Real APT bytecode navigation and read-only selected-stadium scope."""
import os,tempfile,unittest
from pathlib import Path
import build_apt as screen
from native_review_vm import open_native

class StadiumViewTests(unittest.TestCase):
 def test_fifth_card_rows_controller_mouse_toggle_and_back(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'browser.big';screen.build(Path(os.environ['SERVER16_GAME_ROOT']),path)
   vm,view,_,calls=open_native(path,screen.FULL)
   if not view.get('screenReady'):vm.invoke(view.get('Ready'),view)
   def press(code):vm.invoke(view.get('LocalEventHandler'),view,(code,True))
   def sent():return [a[2] for n,a in calls if n=='SendSystemEvent' and a[1]=='Server16ClubBrowser']
   press(2);self.assertEqual(view.get('navPage'),1)
   self.assertEqual(view.get('hubIndex'),1)
   press(4);self.assertEqual(view.get('hubIndex'),4);self.assertEqual(sent()[-1],'focus_stadium')
   press(6);self.assertEqual(view.get('hubIndex'),4)
   press(3);self.assertEqual(view.get('hubIndex'),1)
   button=view.get('scene0').get('action6');self.assertTrue(button.get('_visible'))
   vm.invoke(button.get('onRollOver'),button);vm.invoke(button.get('onRelease'),button)
   self.assertEqual(view.get('navPage'),7);self.assertEqual(sent()[-1],'stadium')
   self.assertFalse(button.get('_visible'));self.assertFalse(view.get('scene0').get('action7'))
   before=len(sent());press(17);self.assertEqual(sent()[-1],'stadium_free');self.assertEqual(len(sent()),before+1)
   press(10);self.assertEqual(sent()[-1],'stadium_pad_toggle');self.assertEqual(len(sent()),before+2)
   help_items=dict(vm.invoke(view.get('getHelpContext'),view))
   self.assertEqual(help_items['OPTION_TOP'],'Primeira pessoa')
   self.assertEqual(help_items['OPTION_LEFT'].encode('latin1').decode('utf-8'),'Câmera livre')
   self.assertEqual(help_items['L1R1'],'Descer / subir')
   press(1);self.assertEqual(view.get('navPage'),1);self.assertEqual(view.get('hubIndex'),4)
   before=len(sent());press(17);self.assertEqual(len(sent()),before)
   press(2);self.assertEqual(view.get('navPage'),7)
   press(1);press(1);self.assertEqual(view.get('navPage'),0)
   self.assertFalse(any('Budget' in n or 'Database' in n for n,_ in calls))

if __name__=='__main__':unittest.main(verbosity=2)
