import hashlib,json,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from loans import BANKS,empty,borrow,request_loan,decide_loan,advance,quote
import runtime as bridge
import save_sidecar as sql

class PortableSaveTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.save=self.root/'slotA/DATA';self.save.parent.mkdir();self.save.write_bytes(b'native FIFA save')
  self.digest=hashlib.sha256(self.save.read_bytes()).hexdigest()
  self.saved=dict(hash=self.digest,date=20260102,budget=17_000_000,club=1629)
  self.io=dict(operation='write',complete_file='1',access_tick_ms='11')
  self.state,self.budget,_=borrow(empty(1629,20260102),request_id='loan',club=1629,today=20260102,budget=16_000_000,bank=3,amount=1_000_000,months=12)

 def test_portable_folder_preserves_debt_payments_and_idempotency_without_modifying_data(self):
  state,budget,_=advance(self.state,club=1629,today=20260202,budget=self.budget)
  saved=dict(self.saved,date=20260202,budget=budget)
  sql.save_snapshot(self.save,saved,state,[dict(id='notice')],self.io)
  target=self.root/'other PC/slotA';shutil.copytree(self.save.parent,target)
  restored=sql.load_snapshot(target/'DATA',self.digest,1629)
  self.assertEqual(restored['state'],state);self.assertEqual(restored['notifications'],[dict(id='notice')])
  again,after,events=advance(restored['state'],club=1629,today=20260202,budget=budget)
  self.assertEqual(after,budget);self.assertFalse(events)
  self.assertEqual(self.save.read_bytes(),b'native FIFA save')
  with sql.connection(self.save) as db:
   self.assertEqual(db.execute("SELECT amount,applied FROM operations WHERE kind='credit'").fetchone(),(1_000_000,1))
   self.assertEqual(db.execute("SELECT count(*) FROM installments WHERE paid_date IS NOT NULL").fetchone()[0],1)

 def test_incomplete_or_different_native_save_cannot_adopt_the_current_ledger(self):
  with self.assertRaises(ValueError):sql.save_snapshot(self.save,self.saved,self.state,[],dict(self.io,complete_file='0'))
  with self.assertRaises(ValueError):sql.save_snapshot(self.save,dict(self.saved,hash='wrong'),self.state,[],self.io)
  sql.save_snapshot(self.save,self.saved,self.state,[],self.io)
  self.assertIsNone(sql.load_snapshot(self.save,'older hash',1629))
  with self.assertRaises(ValueError):sql.load_snapshot(self.save,self.digest,1043)

 def test_pending_proposal_keeps_submission_and_rate_when_sql_bank_settings_change(self):
  state,_,_=request_loan(empty(1629,20260102),request_id='pending',club=1629,today=20260102,budget=16_000_000,bank=3,amount=1_000_000,months=12)
  old=BANKS[3]['rate_bps'];sql.bank_rows(self.save)
  with sql.connection(self.save) as db:db.execute('UPDATE bank_catalog SET rate_bps=150 WHERE bank_id=3')
  rows=sql.bank_rows(self.save);self.assertEqual(next(r[3] for r in rows if r[0]==3),150)
  try:
   BANKS[3]['rate_bps']=150
   decided,_,_,_=decide_loan(state,club=1629,today=state['application']['decision_date'],budget=16_000_000)
   self.assertEqual(decided['contracts'][0]['rate_bps'],old)
   self.assertEqual(decided['contracts'][0]['application_date'],20260102)
   self.assertEqual(quote(3,1_000_000,12)['rate_bps'],150)
  finally:BANKS[3]['rate_bps']=old

 def test_complete_native_write_captures_pending_request_even_when_data_bytes_are_unchanged(self):
  state,_,_=request_loan(empty(1629,20260102),request_id='pending',club=1629,today=20260102,budget=16_000_000,bank=3,amount=1_000_000,months=12)
  saved=dict(self.saved,budget=16_000_000)
  b=bridge.Bridge.__new__(bridge.Bridge);b.scope='scope';b.club=1629;b.memory=None
  current=dict(path=str(self.save),size=self.save.stat().st_size,mtime_ns=self.save.stat().st_mtime_ns)
  b.save=dict(current);b.io_tick=10;b.state=state;b.snapshots=self.root/'scope/snapshots';b.snapshots.mkdir(parents=True)
  b.io_record=lambda:self.io;b.saved=lambda:saved;b.live=lambda:dict(club=1629,date=20260102,budget=16_000_000)
  with patch.object(bridge,'STATE',self.root),patch.object(bridge,'GAME',self.root),patch.object(bridge,'read_active_save',return_value=current),patch.object(bridge,'log'):
   b.observe_save()
  restored=sql.load_snapshot(self.save,self.digest,1629)['state']
  self.assertEqual(restored['application']['date'],20260102);self.assertEqual(restored['application']['decision_date'],20260105)
  self.assertEqual(restored['contracts'],[])

 def test_live_journal_updates_status_without_creating_a_second_financial_operation(self):
  row=dict(session='test',reason='loan_confirmed',native_io_tick=10,before=dict(date=20260102,budget=16_000_000),after_budget=17_000_000,events=[dict(event='credit',id='loan')],status='prepared')
  sql.write_journal(self.save,row);row['status']='applied_in_ram_awaiting_native_save';sql.write_journal(self.save,row)
  with sql.connection(self.save) as db:
   self.assertEqual(db.execute('SELECT status,delta FROM live_operations').fetchall(),[('applied_in_ram_awaiting_native_save',1_000_000)])
