from pathlib import Path
from contextlib import closing
import hashlib,json,sqlite3,tempfile,unittest
from test_engine import catalog,context,matches
from engine import Market
from club_profile import read,spell

class ClubProfileTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.save=self.root/'saves/slot/DATA';self.save.parent.mkdir(parents=True);self.save.write_bytes(b'untouched');catalog(self.root/'catalog.db');self.m=Market(self.save.parent.parent/'server16_manager_market.sqlite3',self.root/'catalog.db');self.m.open_save('saved',self.save,context())
  with self.m.db:self.m.advance(context(20260120,matches(5)))
  self.saved=dict(pid=10,process_created_100ns=20,path=str(self.save));self.profile=dict(context_address=30,context_epoch=2,club_id=3);self.runtime=self.root/'ModCarrerMode/runtime';self.state=self.runtime/'manager_market/state_ready.json';self.state.parent.mkdir(parents=True);self.io();self.ready()
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def io(self,tick='100'):(self.runtime/'career_save_source.tsv').write_text('complete_file=1\npid=10\nprocess_created_100ns=20\noperation=read\naccess_tick_ms='+tick+'\npath='+str(self.save)+'\n')
 def ready(self,**overrides):
  state=dict(schema=1,pid=10,created=20,context=30,epoch=2,club=3,date=20260120,digest='saved',save=str(self.save),database=str(self.m.path),branch=self.m.branch,io=['read','100',str(self.save)]);state.update(overrides);self.state.write_text(json.dumps(state))
 def test_selected_club_uses_verified_branch_and_sql_is_read_only(self):
  before=hashlib.sha256(self.m.path.read_bytes()).hexdigest();data=read(self.root,self.saved,self.profile,20260120,1,'saved');self.assertEqual('Treinador 1',data['coach']['name']);self.assertEqual(1,data['appointment']['club_id']);self.assertEqual(5,len(data['results']));self.assertEqual(before,hashlib.sha256(self.m.path.read_bytes()).hexdigest());self.assertEqual(b'untouched',self.save.read_bytes())
 def test_windows_extended_native_database_path_is_the_same_file(self):
  self.ready(database='\\\\?\\'+str(self.m.path.resolve()));self.assertIsNotNone(read(self.root,self.saved,self.profile,20260120,1,'saved'))
 def test_other_load_owner_epoch_date_hash_or_branch_cannot_leak(self):
  for fields in ({'pid':11},{'created':21},{'epoch':3},{'context':31},{'club':1},{'date':20260121},{'digest':'other'},{'branch':'unknown'},{'save':str(self.save.with_name('OTHER'))}):
   self.ready(**fields);self.assertIsNone(read(self.root,self.saved,self.profile,20260120,1,'saved'))
  self.ready();self.io('101');self.assertIsNone(read(self.root,self.saved,self.profile,20260120,1,'saved'))
 def test_renewal_keeps_spell_but_return_after_dismissal_does_not(self):
  coach=self.m.one('coaches','coach_id','1');club=self.m.one('clubs','club_id',1);original=self.m.active(club=1)['id']
  with self.m.db:self.m.leave(self.m.active(club=1),20260120,'renewed','Renovação');self.m.appoint(coach,club,20260120,'renewal')
  data=spell(self.m.db,self.m.branch,1,20260120);self.assertEqual(20260101,data['start']);self.assertIn(original,data['appointments']);self.assertEqual(2,len(data['appointments']))
  with self.m.db:self.m.leave(self.m.active(club=1),20260120,'dismissal','Teste');self.m.appoint(coach,club,20260120,'hired')
  data=spell(self.m.db,self.m.branch,1,20260120);self.assertEqual(20260120,data['start']);self.assertEqual(1,len(data['appointments']));self.assertNotIn(original,data['appointments'])

if __name__=='__main__':unittest.main()
