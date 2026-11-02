from pathlib import Path
import hashlib,json,sqlite3,struct,sys,tempfile,unittest
sys.path.append(str(Path(__file__).resolve().parents[2]/'club_browser'))
from model_assets import actor,catalog,fixture,publication

class CareerModelsTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.key='COACH-0123456789abcdef';self.row=dict(coachId=self.key,assetId=14,files={})
  self.folder=self.root/'data/sceneassets/manager_market/14';self.folder.mkdir(parents=True)
  for weather in (0,1):
   for suffix in ('','_textures'):
    name=f'model_{weather}{suffix}.rx3';blob=name.encode();(self.folder/name).write_bytes(blob);self.row['files'][name]=hashlib.sha256(blob).hexdigest()
  self.registry=self.root/'ModCarrerMode/data/manager_market/manager_models.json';self.registry.parent.mkdir(parents=True);self.write()
  self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.db.executescript('CREATE TABLE branches(id,game_date,user_club);INSERT INTO branches VALUES("b",20261123,1043);CREATE TABLE appointments(branch,club_id,coach_id,end_date,start_date);')
  self.state=dict(branch='b',date=20261123,club=1043,pid=5,created=11,context=1234,epoch=2,io=['read','30','C:/save/DATA'],digest='d',revision='r')
 def tearDown(self):self.db.close();self.temp.cleanup()
 def write(self,**extra):
  data=dict(schema=2,runtimeOverrideEnabled=True,coaches=[self.row]);data.update(extra);self.registry.write_text(json.dumps(data))
 def market(self,key=None):return dict(coach=dict(coach_id=key or self.key),appointment=dict(id='new'))
 def test_transferred_coach_resolves_person_not_destination_club(self):
  selected=actor(self.root,self.market());self.assertEqual(14,selected['assetId']);self.assertEqual('new',selected['appointment'])
  request=fixture(struct.pack('<8s4I',b'FFCOACH1',1629,1,2,3),selected)
  self.assertEqual((b'FFCOACH2',1629,1,2,3,14),struct.unpack('<8s5I',request))
 def test_unknown_human_or_unverified_does_not_show_predecessor(self):
  for market in (None,self.market('COACH-ffffffffffffffff'),self.market('USER-0')):self.assertIsNone(actor(self.root,market))
 def test_missing_or_changed_pair_never_mixes_assets(self):
  self.assertIsNotNone(actor(self.root,self.market()));(self.folder/'model_1_textures.rx3').unlink();self.assertIsNone(actor(self.root,self.market()))
  (self.folder/'model_1_textures.rx3').write_bytes(b'wrong');self.assertIsNone(actor(self.root,self.market()))
 def test_disabled_duplicate_or_legacy_catalog_fails_closed(self):
  for change in (dict(schema=1),dict(runtimeOverrideEnabled=False),dict(coaches=[self.row,self.row])):self.write(**change);self.assertEqual({},catalog(self.root))
 def test_current_contracts_only_and_absent_models_are_explicit_zero(self):
  self.db.executemany('INSERT INTO appointments VALUES(?,?,?,?,?)',[('b',1629,self.key,20261120,20260101),('b',1629,'COACH-ffffffffffffffff',None,20261120),('b',383,self.key,None,20261120),('other',1629,self.key,None,20260101)])
  publication(self.root,self.db,self.state);p=self.root/'ModCarrerMode/runtime/manager_market/models_ready.tsv';text=p.read_text();self.assertIn('row=1629|0',text);self.assertIn('row=383|14',text);self.assertEqual(2,text.count('row='));before=p.stat().st_mtime_ns;publication(self.root,self.db,self.state);self.assertEqual(before,p.stat().st_mtime_ns)
 def test_wrong_branch_day_or_duplicate_contract_rejected(self):
  for change in (dict(branch='missing'),dict(date=20261122),dict(club=1629)):
   with self.assertRaises(ValueError):publication(self.root,self.db,dict(self.state,**change))
  self.db.executemany('INSERT INTO appointments VALUES(?,?,?,?,?)',[('b',1629,self.key,None,20260101),('b',1629,self.key,None,20260102)])
  with self.assertRaises(ValueError):publication(self.root,self.db,self.state)

if __name__=='__main__':unittest.main()
