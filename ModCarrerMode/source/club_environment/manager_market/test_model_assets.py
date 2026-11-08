from pathlib import Path
import sqlite3,struct,sys,tempfile,unittest
sys.path.append(str(Path(__file__).resolve().parents[2]/'club_browser'))
from model_assets import actor,catalog,fixture,publication

class CareerModelsTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.key='COACH-0123456789abcdef';self.slc=14
  folder=self.root/'data/sceneassets/slc';folder.mkdir(parents=True)
  for weather in (0,1):
   for suffix in ('','_textures'):(folder/f'specificmanager_{self.slc}_0_{weather}{suffix}.rx3').write_bytes(b'RX3l'+b'\0'*28)
  self.registry=self.root/'ModCarrerMode/data/manager_market/manager_registry.ini';self.registry.parent.mkdir(parents=True);self.write()
  self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.db.executescript('CREATE TABLE branches(id,game_date,user_club);INSERT INTO branches VALUES("b",20261123,1043);CREATE TABLE appointments(branch,club_id,coach_id,end_date,start_date);')
  self.state=dict(branch='b',date=20261123,club=1043,pid=5,created=11,context=1234,epoch=2,io=['read','30','C:/save/DATA'],digest='d',revision='r')
 def tearDown(self):self.db.close();self.temp.cleanup()
 def write(self,enabled='true',model='true',source='14'):
  self.registry.write_text('[registry]\nschema=1\nenabled=true\n\n[coach:'+self.key+']\nname=Coach Example\nnationality=Brazil\nbirth_date=1970-01-01\nbirthplace=Rio\nreputation=7\nsalary=50000\nstyle=Balanced\nimage=minifaces/NOTFOUND_DEFAULT.png\nmarket_enabled=true\nfictional=false\ndefault_club_id=1629\nsource_slc_club_id='+source+'\nmodel_enabled='+model+'\n',encoding='utf8')
 def market(self,key=None):return dict(coach=dict(coach_id=key or self.key),appointment=dict(id='new'))
 def test_transferred_coach_resolves_person_to_native_slc_model(self):
  selected=actor(self.root,self.market());self.assertEqual(14,selected['assetId']);self.assertEqual('new',selected['appointment']);self.assertTrue(selected['base'].startswith('data/sceneassets/slc/specificmanager_14_'))
  request=fixture(struct.pack('<8s4I',b'FFCOACH1',1629,1,2,3),selected)
  self.assertEqual((b'FFCOACH2',1629,1,2,3,14),struct.unpack('<8s5I',request))
 def test_unknown_coach_or_missing_native_variant_does_not_show_predecessor(self):
  self.assertIsNone(actor(self.root,self.market('COACH-ffffffffffffffff')))
  selected=actor(self.root,self.market());self.assertIsNotNone(selected)
  (self.root/'data/sceneassets/slc/specificmanager_14_0_1_textures.rx3').unlink();self.assertIsNone(actor(self.root,self.market()))
 def test_disabled_or_invalid_registry_fails_closed(self):
  self.write(model='false');self.assertEqual({},catalog(self.root))
  self.write(source='0');self.assertEqual({},catalog(self.root))
  self.registry.write_text('[registry]\nschema=2\nenabled=true\n',encoding='utf8');self.assertEqual({},catalog(self.root))
 def test_current_contracts_only_map_to_native_slc_and_unknown_to_zero(self):
  self.db.executemany('INSERT INTO appointments VALUES(?,?,?,?,?)',[('b',1629,self.key,20261120,20260101),('b',1629,'COACH-ffffffffffffffff',None,20261120),('b',383,self.key,None,20261120),('other',1629,self.key,None,20260101)])
  publication(self.root,self.db,self.state);p=self.root/'ModCarrerMode/runtime/manager_market/models_ready.tsv';text=p.read_text();self.assertIn('row=1629|0',text);self.assertIn('row=383|14',text);self.assertEqual(2,text.count('row='));before=p.stat().st_mtime_ns;publication(self.root,self.db,self.state);self.assertEqual(before,p.stat().st_mtime_ns)
 def test_wrong_branch_day_or_duplicate_contract_rejected(self):
  for change in (dict(branch='missing'),dict(date=20261122),dict(club=1629)):
   with self.assertRaises(ValueError):publication(self.root,self.db,dict(self.state,**change))
  self.db.executemany('INSERT INTO appointments VALUES(?,?,?,?,?)',[('b',1629,self.key,None,20260101),('b',1629,self.key,None,20260102)])
  with self.assertRaises(ValueError):publication(self.root,self.db,self.state)

if __name__=='__main__':unittest.main()
