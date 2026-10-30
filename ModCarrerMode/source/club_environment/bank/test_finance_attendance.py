"""Per-match crowds, calendar catch-up, cash reconciliation and native reload."""
import copy,hashlib,json,sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import club_finance as finance
import match_attendance as crowd
import save_sidecar as sql
from loans import empty
from test_club_finance import context,match,step

class MatchAttendanceTests(unittest.TestCase):
 def setUp(self):self.state,self.budget,_=step(empty(1043,20260511))
 def fixture(self,i,day,percent,**extra):
  return dict(match(i,day,**extra),attendance=dict(percent=percent,source='crowd_reconstructed',actual=False))
 def test_calendar_batch_uses_each_fixture_crowd_and_reconciles_cash(self):
  games=[self.fixture(1,20260512,30),self.fixture(2,20260515,60),self.fixture(3,20260518,80,home=567,away=1043)]
  state,budget,events=step(self.state,20260520,self.budget,games)
  receipts=[e for e in state['finance']['entries'] if e['kind']=='tickets']
  self.assertEqual([e['attendance'] for e in receipts],[15000,30000])
  self.assertEqual([e['amount'] for e in receipts],[120000,240000])
  self.assertEqual([e['crowd_percent'] for e in receipts],[30,60])
  self.assertEqual(budget-self.budget,finance.cash_delta(events))
  self.assertEqual(sum(-e['amount'] for e in events if e['kind']=='match_costs'),144000)
  again,same,events=step(state,20260520,budget,games)
  self.assertEqual(same,budget);self.assertFalse(events);self.assertEqual(state,again)
 def test_observed_crowd_overrides_estimate_and_never_reprices_receipt(self):
  reading=dict(id=1,root=7,date=20260512,home=1043,away=567,percent=43,
               source='crowd_match_applied',actual=True,capacity=19086,observed_date=20260511)
  state,changed=finance.record_attendance(self.state,reading,20260511);self.assertTrue(changed)
  state,changed=finance.record_attendance(state,dict(reading,percent=20,actual=False),20260511);self.assertFalse(changed)
  state,budget,_=step(state,20260512,self.budget,[self.fixture(1,20260512,60)])
  entry=next(e for e in state['finance']['entries'] if e['kind']=='tickets')
  self.assertEqual((entry['attendance'],entry['amount']),(8207,65656));self.assertTrue(entry['crowd_actual'])
  original=copy.deepcopy(state)
  state,changed=finance.record_attendance(state,dict(reading,percent=90),20260512);self.assertFalse(changed)
  state,same,events=step(state,20260512,budget,[self.fixture(1,20260512,90)])
  self.assertEqual(state,original);self.assertEqual(same,budget);self.assertFalse(events)
 def test_zero_crowd_full_crowd_and_neutral_are_explicit(self):
  games=[self.fixture(1,20260512,0),self.fixture(2,20260515,100),self.fixture(3,20260518,80,neutral=True)]
  state,_,_=step(self.state,20260520,self.budget,games)
  tickets=[e for e in state['finance']['entries'] if e['kind']=='tickets']
  self.assertEqual([e['attendance'] for e in tickets],[0,50000])
  with self.assertRaises(ValueError):finance.ticket_projection(50000,10,occupancy_percent=101)
 def test_unplayed_future_fixture_does_not_generate_cash(self):
  state,budget,events=step(self.state,20260512,self.budget,[self.fixture(1,20260512,60,played=False)])
  self.assertEqual(budget,self.budget);self.assertFalse(events)
 def test_disabled_ticket_income_does_not_create_operation_debit(self):
  state=finance.toggle(self.state,'tickets',False,20260511)
  state,budget,events=step(state,20260512,self.budget,[self.fixture(1,20260512,60)])
  self.assertEqual([e['kind'] for e in events],['tv'])
  self.assertEqual([e['status'] for e in state['finance']['entries'] if e['kind'] in ('tickets','match_costs')],['disabled','disabled'])
 def test_reconstruction_changes_with_opponent_and_prior_results_only(self):
  teams={1043:dict(domesticprestige=8,internationalprestige=4),567:dict(domesticprestige=2,internationalprestige=0),568:dict(domesticprestige=20,internationalprestige=20)}
  fixture=match(5,20260520)
  before=dict(match(1,20260514),homeScore=0,awayScore=4)
  after=dict(match(2,20260525),homeScore=5,awayScore=0)
  a=crowd.reconstruct(fixture,1043,[before],teams,3)
  self.assertEqual(a,crowd.reconstruct(fixture,1043,[before,after],teams,3))
  good=dict(before,homeScore=4,awayScore=0)
  self.assertGreater(crowd.reconstruct(fixture,1043,[good],teams,3)['percent'],a['percent'])
  self.assertGreater(crowd.reconstruct(dict(fixture,away=568),1043,[before],teams,3)['percent'],a['percent'])
  self.assertEqual(a['source'],'crowd_reconstructed');self.assertFalse(a['actual'])
 def test_semifinal_and_final_flags_are_not_third_place(self):
  m=match();teams={1043:dict(domesticprestige=6),567:dict(domesticprestige=6)}
  third=crowd.reconstruct(dict(m,stageKind=9),1043,[],teams,3)
  semi=crowd.reconstruct(dict(m,stageKind=8),1043,[],teams,3)
  final=crowd.reconstruct(dict(m,stageKind=10),1043,[],teams,3)
  self.assertGreater(semi['percent'],third['percent']);self.assertGreaterEqual(final['percent'],90)
 def test_native_checkpoint_preserves_counts_without_touching_data(self):
  state,budget,_=step(self.state,20260520,self.budget,[self.fixture(1,20260512,37),self.fixture(2,20260515,63)])
  with tempfile.TemporaryDirectory() as folder:
   save=Path(folder)/'DATA';save.write_bytes(b'native bytes only written by this test fixture');raw=save.read_bytes();digest=hashlib.sha256(raw).hexdigest()
   saved=dict(club=1043,date=20260520,budget=budget,hash=digest)
   sql.save_snapshot(save,saved,state,[],dict(operation='write',complete_file='1',access_tick_ms=99))
   restored=sql.load_snapshot(save,digest,1043)['state'];self.assertEqual(restored,state)
   with closing(sqlite3.connect(sql.path_for(save))) as db:
    self.assertEqual(db.execute('SELECT count(*) FROM finance_attendance').fetchone()[0],2)
    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
   self.assertEqual(save.read_bytes(),raw)
   _,same,events=step(restored,20260520,budget,[self.fixture(1,20260512,99)])
   self.assertEqual(same,budget);self.assertFalse(events)
 def test_current_static_percent_is_not_used_to_reconstruct_past_matches(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'ModCarrerMode').mkdir();ini=root/'ModCarrerMode/crowd.ini'
   ini.write_text('[crowd]\nautomatic_dynamic_controller=1\nstatic_factor_percent=60\n[crowd_weights]\nlast_results=nan\nbase=-2\n')
   cfg=crowd.config(root);self.assertEqual(cfg['weights']['last_results'],crowd.WEIGHTS['last_results']);self.assertEqual(cfg['weights']['base'],crowd.WEIGHTS['base'])
   m=match();a=crowd.reconstruct(m,1043,[],{},3,weights=cfg['weights'])
   ini.write_text('[crowd]\nautomatic_dynamic_controller=1\nstatic_factor_percent=20\n')
   self.assertEqual(a,crowd.reconstruct(m,1043,[],{},3,weights=crowd.config(root)['weights']))
 def test_observation_belongs_to_verified_session_and_one_upcoming_fixture(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);runtime=root/'ModCarrerMode/runtime';runtime.mkdir(parents=True)
   save=root/'DATA';save.write_bytes(b'save')
   snap=dict(schema=3,pid=77,club=1043,date=20260511,savePath=str(save),processCreated100ns=12,
             nodes=[[7,0,3,7],[8,7,4,7]],fixtures=[[1,8,8,20260512,1800,1043,567,0,0,0]])
   path=runtime/'career_fce_snapshot.json';path.write_text(json.dumps(snap))
   live=dict(club=1043,date=20260511)
   with patch.object(crowd,'shared_percent',return_value=dict(percent=53,source='crowd_match_applied',actual=True)):
    row=crowd.observe(root,save,live,pid=77,created=12);self.assertEqual((row['id'],row['percent']),(1,53))
    self.assertIsNone(crowd.observe(root,save,live,pid=78,created=12))
    self.assertIsNone(crowd.observe(root,save,live,pid=77,created=13))
    self.assertIsNone(crowd.observe(root,save,dict(live,date=20260512),pid=77,created=12))
   ini=root/'ModCarrerMode/crowd.ini'
   ini.write_text('[crowd]\nautomatic_dynamic_controller=1\nstatic_factor_percent=60\n')
   with patch.object(crowd,'shared_percent',return_value=None):
    self.assertIsNone(crowd.observe(root,save,live,pid=77,created=12))
    ini.write_text('[crowd]\nautomatic_dynamic_controller=0\nstatic_factor_percent=0\n')
    self.assertEqual(crowd.observe(root,save,live,pid=77,created=12)['percent'],0)

 def test_preview_gross_uses_the_same_crowd_as_displayed_attendance(self):
  from preview_details import finance_gate
  for percent in (0,37,63,100):
   gate=finance_gate('',None,1043,20260101,7,1043,False,19086,10,20260512,occupancy_percent=percent)
   self.assertEqual(gate['attendance'],(19086*percent+50)//100)
   self.assertEqual(gate['gross'],gate['attendance']*gate['ticket_price'])
   away=finance_gate('',None,1043,20260101,7,567,False,19086,10,20260512,occupancy_percent=percent)
   self.assertEqual(away['gross'],0)

 def test_reject_stale_unacknowledged_and_foreign_match_percentages(self):
  from types import SimpleNamespace
  row=dict(game_pid=77,owner_pid=12,heartbeat=1000,phase=2,home_id=1043,away_id=567,command=5,ack=5,status=2,current_percent=61)
  self.assertEqual(crowd.validated_shared(SimpleNamespace(**row),77,1043,567,1100)['percent'],61)
  for change in (dict(game_pid=78),dict(owner_pid=0),dict(heartbeat=1),dict(phase=0),dict(home_id=8),dict(away_id=8),dict(command=-5),dict(ack=4),dict(status=4),dict(current_percent=-1),dict(current_percent=101)):
   with self.subTest(change=change):self.assertIsNone(crowd.validated_shared(SimpleNamespace(**dict(row,**change)),77,1043,567,4000))

if __name__=='__main__':unittest.main()
