import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import runtime as r
import save_sidecar as sql
from loans import empty,borrow,advance,presentation

class ClubSwitchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.data=self.root/'slot/DATA';self.data.parent.mkdir();self.data.write_bytes(b'career before job change')
  self.digest=hashlib.sha256(self.data.read_bytes()).hexdigest()
  self.save=dict(path=str(self.data),process_created_100ns=123,size=self.data.stat().st_size,mtime_ns=1)
  self.saved=dict(hash=self.digest,club=1629,userid=0,date=20260206,budget=16_000_000,wage_budget=100_000,currency=0)
  self.live=dict(club=517,date=20260208,budget=24_500_000,address=0x12ac,page=r.PAGE,context_epoch=3)
  self.profile=dict(userid=0,club_id=517,career_role=1,context_address=0x1000,context_epoch=3)
  self.io=dict(operation='read',complete_file='1',access_tick_ms='10')
  self.old,budget,_=borrow(empty(1629,20260206),request_id='old-club-loan',club=1629,today=20260206,budget=16_000_000,bank=3,amount=1_000_000,months=12)

 def test_native_job_change_attaches_to_new_club_before_the_next_fifa_save(self):
  shown=[];kernel=SimpleNamespace(OpenProcess=lambda *_:1)
  memory=SimpleNamespace(kernel32=kernel,_get_base_address=lambda _:0x140000000,read_uint32=lambda _:100_000,close=lambda:None)
  process=SimpleNamespace(pid=987654321,exe=lambda:'fifa16.exe')
  bridge=r.Bridge.__new__(r.Bridge)
  def publish(bridge,live):shown.append(presentation(bridge.state,live['date'],live['budget'],wage_budget=bridge.memory.read_uint32(0)))
  with patch.object(r,'STATE',self.root/'runtime'),patch.object(r,'GAME',self.root),patch.object(r,'log'), \
       patch.object(r.portable,'session_process',return_value=process),patch.object(r,'Memory',return_value=memory), \
       patch.object(r,'competition_session',return_value=self.profile),patch.object(r,'read_active_save',return_value=self.save), \
       patch.object(r.Bridge,'saved',return_value=self.saved),patch.object(r.Bridge,'live',return_value=self.live),patch.object(r.Bridge,'publish_view',publish):
   try:r.Bridge.__init__(bridge,apply=False)
   finally:bridge.close()
  self.assertEqual(bridge.club,517);self.assertEqual(bridge.state['club'],517)
  self.assertEqual(shown[0]['budget'],24_500_000);self.assertEqual(shown[0]['wage_budget'],100_000)
  self.assertEqual(bridge.state['contracts'],[])

 def test_previous_club_debt_is_archived_without_charging_the_new_club(self):
  sql.save_snapshot(self.data,dict(self.saved,budget=17_000_000),self.old,[],dict(self.io,operation='write'))
  with patch.object(r,'STATE',self.root/'runtime'):
   clubs=r.career_clubs(self.save,self.saved,self.live,self.profile,'session',self.io)
  self.assertEqual(clubs[1629]['state']['contracts'][0]['principal'],1_000_000)
  self.assertNotIn(517,clubs)
  new,budget,events=advance(empty(517,self.live['date']),club=517,today=20260308,budget=self.live['budget'])
  self.assertEqual(budget,24_500_000);self.assertFalse(events)
  saved=dict(self.saved,club=517,date=20260308,budget=budget)
  sql.save_snapshot(self.data,saved,new,[],dict(self.io,operation='write'),clubs=clubs)
  restored=sql.load_clubs(self.data,self.digest)
  self.assertEqual(set(restored),{1629,517});self.assertTrue(restored[1629]['state']['contracts'])
  self.assertEqual(restored[517]['state']['contracts'],[])

 def test_same_process_recovery_survives_worker_restart_but_a_later_load_discards_unsaved_state(self):
  sql.save_session_club(self.data,self.digest,'session',10,self.old,[])
  self.assertIn(1629,sql.load_session_clubs(self.data,self.digest,'session',self.io))
  self.assertFalse(sql.load_session_clubs(self.data,self.digest,'another process',self.io))
  self.assertFalse(sql.load_session_clubs(self.data,self.digest,'session',dict(self.io,access_tick_ms='11')))
  self.assertFalse(sql.load_session_clubs(self.data,'another save','session',self.io))

 def test_native_save_after_job_change_keeps_both_clubs_and_reloading_the_older_save_keeps_its_old_state(self):
  sql.save_snapshot(self.data,self.saved,empty(1629,20260206),[],dict(self.io,operation='write'))
  old_hash=self.digest;self.data.write_bytes(b'career after joining Botafogo')
  new_hash=hashlib.sha256(self.data.read_bytes()).hexdigest()
  clubs={1629:dict(state=self.old,notifications=[])}
  sql.save_snapshot(self.data,dict(self.saved,hash=new_hash,club=517,date=20260208,budget=24_500_000),empty(517,20260208),[],dict(self.io,operation='write'),clubs=clubs)
  self.assertEqual(sql.load_clubs(self.data,old_hash)[1629]['state']['contracts'],[])
  self.assertTrue(sql.load_clubs(self.data,new_hash)[1629]['state']['contracts'])
  self.assertNotIn(517,sql.load_clubs(self.data,old_hash))

 def test_foreign_manager_or_rewound_calendar_cannot_adopt_the_financial_context(self):
  with self.assertRaises(RuntimeError):r.career_clubs(self.save,self.saved,self.live,dict(self.profile,userid=1),'session',self.io)
  with self.assertRaises(RuntimeError):r.career_clubs(self.save,self.saved,dict(self.live,date=20260101),self.profile,'session',self.io)

 def test_schema_one_is_migrated_without_changing_the_native_data_or_old_debt(self):
  import sqlite3
  db=sqlite3.connect(sql.path_for(self.data))
  try:
   db.execute('CREATE TABLE snapshots(save_hash TEXT PRIMARY KEY,club INTEGER,game_date INTEGER,budget INTEGER,native_io_tick INTEGER,state_json TEXT,notifications_json TEXT)')
   db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?,?)',(self.digest,1629,20260206,17_000_000,10,json.dumps(self.old),'[]'))
   db.execute('PRAGMA user_version=1');db.commit()
  finally:db.close()
  self.assertEqual(sql.load_clubs(self.data,self.digest)[1629]['state'],self.old)
  self.assertEqual(self.data.read_bytes(),b'career before job change')
