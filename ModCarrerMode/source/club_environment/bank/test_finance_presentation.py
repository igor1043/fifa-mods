from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest,json
import finance_presentation as presentation

class FinancePresentationTest(unittest.TestCase):
 def test_previous_epoch_snapshot_cannot_be_used_even_on_same_date_and_slot(self):
  from finance_inputs import FinanceInputs
  with TemporaryDirectory() as folder:
   root=Path(folder);save=root/'DATA';save.write_bytes(b'native')
   runtime=root/'ModCarrerMode/runtime';runtime.mkdir(parents=True)
   snapshot=dict(schema=3,pid=10,club=1043,date=20260101,savePath=str(save),processCreated100ns=20,fceContextEpoch=6)
   (runtime/'career_fce_snapshot.json').write_text(json.dumps(snapshot))
   reader=FinanceInputs(root)
   with self.assertRaisesRegex(ValueError,'recarregada'):
    reader.read(save,dict(club=1043,date=20260101,context_epoch=7),pid=10,userid=0,created=20)
   self.assertIsNone(reader.last);self.assertIsNone(reader.cache)

 def test_reload_removes_previous_career_data_and_readiness_without_touching_save(self):
  with TemporaryDirectory() as folder:
   root=Path(folder);runtime=root/'runtime';runtime.mkdir();source=root/'waiting.big';source.write_bytes(b'generic waiting screen')
   target=root/'data/ui/game/screens/career/server16/clubfinance.big';target.parent.mkdir(parents=True);target.write_bytes(b'December figures')
   (runtime/'view_ready.tsv').write_text('old career');(runtime/'club_finance_view.json').write_text('{"ready":true,"entries":["December"]}')
   save=root/'native/slot/DATA';save.parent.mkdir(parents=True);save.write_bytes(b'native save unchanged');ledger=root/'ledger.sqlite3';ledger.write_bytes(b'checkpoint unchanged')
   with patch.object(presentation,'waiting_package',return_value=source):presentation.invalidate(root,runtime)
   self.assertEqual(b'generic waiting screen',target.read_bytes());self.assertFalse((runtime/'view_ready.tsv').exists())
   view=json.loads((runtime/'club_finance_view.json').read_bytes());self.assertFalse(view['ready']);self.assertEqual([],view['entries'])
   self.assertEqual(b'native save unchanged',save.read_bytes());self.assertEqual(b'checkpoint unchanged',ledger.read_bytes())

if __name__=='__main__':unittest.main()
