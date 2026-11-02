from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest
import test_screen
from loading_progress import Progress,scope,scene,build
from native_review_vm import open_native

class ProgressTest(unittest.TestCase):
 def observed(self):return dict(save=dict(pid=42,process_created_100ns=100,path='slot/DATA'),profile=dict(context_address=30,context_epoch=2,club_id=3),date=20260101)
 def test_only_real_stage_changes_advance_and_reloaded_career_resets(self):
  with TemporaryDirectory() as folder:
   path=Path(folder)/'progress.json';p=Progress(path);o=self.observed();io=dict(operation='read',access_tick_ms='1')
   with patch('loading_progress.time.monotonic',return_value=10):p.begin(o,io)
   p.set(2);self.assertEqual(2,json.loads(path.read_bytes())['stage'])
   with patch('loading_progress.time.monotonic',return_value=200):p.begin(o,io)
   self.assertEqual(10000,p.value['started_ms']);self.assertEqual(2,p.value['stage'])
   p.done();self.assertFalse(json.loads(path.read_bytes())['active'])
   o['profile']['context_epoch']=3;p.begin(o,io);self.assertEqual(0,p.value['stage']);self.assertTrue(p.value['active'])
 def test_scope_distinguishes_club_process_load_and_date(self):
  o=self.observed();io=dict(operation='read',access_tick_ms='1');original=scope(o,io)
  self.assertNotEqual(original,scope(o,dict(io,access_tick_ms='2')))
  for mapping,key in ((o,'date'),(o['save'],'pid'),(o['save'],'process_created_100ns'),(o['profile'],'context_address'),(o['profile'],'context_epoch'),(o['profile'],'club_id')):
   old=mapping[key];mapping[key]+=1;self.assertNotEqual(original,scope(o,io));mapping[key]=old
 def test_native_loading_bar_and_original_back_help(self):
  with TemporaryDirectory() as folder:
   output=Path(folder)/'loading.big';build(test_screen.GAME,output,2,123)
   vm,state,apt,calls=open_native(output,full='game.screens.career.server16.ManagerMarket');vm.invoke(state.get('Ready'),state)
   texts=[c.text for c in apt.characters.values() if c.type==2]
   self.assertIn('Em segundo plano',texts);self.assertTrue(any('40%' in s for s in texts));self.assertFalse(any('100%' in s for s in texts))
   self.assertEqual([('BACK','Voltar')],vm.invoke(state.get('getHelpContext'),state))
   # The same native BACK event is used by the existing market controller.
   self.assertEqual([],vm.errors);self.assertLess(output.stat().st_size,20000)
 def test_marker_never_fakes_progress_from_elapsed_time(self):
  self.assertEqual(scene(2,1),scene(2,999))
 def test_ready_market_is_not_replaced_by_progress_on_same_date_refresh(self):
  with TemporaryDirectory() as folder:
   p=Progress(Path(folder)/'progress.json');o=self.observed();io=dict(operation='read',access_tick_ms='1')
   p.begin(o,io);p.set(4);p.set(1);self.assertEqual(4,p.value['stage'])
   p.done();p.begin(o,io);p.set(2);self.assertFalse(p.value['active'])

if __name__=='__main__':unittest.main()
