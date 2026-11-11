import json,tempfile,unittest,zlib
from pathlib import Path
from engine import Market
from test_engine import catalog,context,matches
from durable_store import persist,path as durable_path
from save_database import database_path,import_checkpoint


class DurableStoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.catalog=self.root/'cat.db';catalog(self.catalog)
  self.save=self.root/'slots/A/DATA';self.save.parent.mkdir(parents=True);self.save.write_bytes(b'unchanged native save')
  self.market=Market(database_path(self.save),self.catalog)
  self.market.open_save('initial',self.save,context())
 def tearDown(self):self.market.close();self.temp.cleanup()
 def capture(self,date=20260120,tick=100):
  with self.market.db:self.market.advance(context(date,matches(5)));return self.market.capture_session(10,20,30,2,tick)
 def test_same_revision_is_not_rewritten_and_other_slots_are_separate(self):
  revision=self.capture();before=self.save.read_bytes();first=persist(self.market,self.save,revision,checkpoints=True)
  self.assertGreater(first['states'],0);second=persist(self.market,self.save,revision,checkpoints=True)
  self.assertEqual(dict(states=0,objects=0,checkpoints=0),second)
  self.assertNotEqual(durable_path(self.save),durable_path(self.save.parent.parent/'B/DATA'));self.assertEqual(before,self.save.read_bytes())
 def test_saved_world_survives_native_sql_loss_and_unsaved_future_is_not_restored(self):
  revision=self.capture();self.market.checkpoint('saved',self.save);persist(self.market,self.save,revision,checkpoints=True)
  expected=self.market.snapshot();self.capture(20260220,200);persist(self.market,self.save,full=True)
  old=self.market.path;self.market.close();old.unlink();self.market=Market(old,self.catalog)
  with self.market.db:
   self.assertTrue(import_checkpoint(self.market,self.save,'saved'));self.market.open_save('saved',self.save,context(20260120))
  actual=json.loads(zlib.decompress(self.market.snapshot()));want=json.loads(zlib.decompress(expected));actual['info'].update(id=want['info']['id'],kind=want['info']['kind'])
  self.assertEqual(want,actual);self.assertEqual(20260120,self.market.info()['game_date'])


if __name__=='__main__':unittest.main()
