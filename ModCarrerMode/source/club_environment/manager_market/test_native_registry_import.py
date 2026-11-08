"""New native coach imports must not reassign a running career's contracts."""
from pathlib import Path
import tempfile,unittest
from test_engine import catalog,context
from engine import Market
from coach_registry import load

class NativeRegistryImportTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);catalog(self.root/'catalog.sqlite3');self.market=Market(self.root/'career.sqlite3',self.root/'catalog.sqlite3');self.market.open_save('initial','DATA',context());self.key='COACH-newnative';self.ini=self.root/'manager_registry.ini'
 def tearDown(self):self.market.close();self.temp.cleanup()
 def registry(self,target=1):
  self.ini.write_text('[registry]\nschema=1\nenabled=true\n[coach:'+self.key+']\nname=Native Imported Coach\nnationality=Brasil\nbirth_date=\nbirthplace=\nreputation=6\nsalary=90000\nstyle=Equilibrado\nimage=minifaces/native.png\nmarket_enabled=true\nfictional=false\ndefault_club_id='+str(target)+'\nsource_slc_club_id=190210\nmodel_enabled=true\n',encoding='utf8')
 def test_existing_contracts_and_person_ids_survive_new_model_import(self):
  before=[dict(x) for x in self.market.rows('appointments')];self.registry();self.market.import_new_coaches();self.assertIsNotNone(self.market.one('coaches','coach_id',self.key));self.assertIsNone(self.market.active(coach=self.key));self.assertEqual(before,[dict(x) for x in self.market.rows('appointments')]);self.assertEqual('1',self.market.active(club=1)['coach_id'])
 def test_registry_id_and_native_slc_are_separate_from_destination_club(self):
  self.registry();row=load(self.ini)[self.key];self.assertEqual(190210,row['source_slc_club_id']);self.assertEqual(1,row['default_club_id']);self.assertTrue(row['model_enabled']);self.assertIsNone(row['birth_date'])
 def test_restoring_checkpoint_does_not_apply_new_default_club(self):
  before=self.market.active(club=1)['coach_id'];self.market.checkpoint('saved','DATA');self.registry();self.market.open_save('saved','DATA',context());self.market.import_new_coaches();self.assertEqual(before,self.market.active(club=1)['coach_id']);self.assertIsNone(self.market.active(coach=self.key))

if __name__=='__main__':unittest.main()
