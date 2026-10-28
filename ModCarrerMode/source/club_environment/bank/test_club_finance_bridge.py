import ctypes,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import runtime as r
import club_finance as f
from loans import empty,borrow
from test_club_finance import context

class FinanceBridgeTests(unittest.TestCase):
 def bridge(self,state,today=20260511,budget=10_000_000):
  b=r.Bridge.__new__(r.Bridge);b.apply=True;b.state=state;b.session='test';b.scope='scope';b.io_tick=1;b.saved_hash='hash';b.result=None
  b.process=type('P',(),{'pid':1})();b.context_address=0x1000;b.write_handle=1;b.nonce='B57_1_1043_TEST'
  b.last_sequence=0;b.last_scan=0;b.last_advance=(None,None);b.finance_ack=0;b.finance_signature=None
  live=dict(club=1043,date=today,budget=budget,address=0x1234,page=r.FINANCE_PAGE,context_epoch=3)
  b.live=lambda:dict(live);b.observe_save=lambda:None;b.flush_notifications=lambda _:None;b.publish_view=lambda _:None
  writes=[]
  class Kernel:
   def WriteProcessMemory(self,handle,address,buffer,size,written):
    live['budget']=int.from_bytes(ctypes.string_at(buffer,size),'little');writes.append(live['budget'])
    ctypes.cast(written,ctypes.POINTER(ctypes.c_size_t))[0]=4;return True
  b.memory=type('M',(),{'kernel32':Kernel(),'read_uint32':lambda _,at:live['budget']})()
  return b,live,writes
 def test_master_switch_stops_pending_approval_and_all_money_but_can_reenable(self):
  state,_,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=10_000_000,context=context())
  state['application']=dict(id='pending',decision_date=20260512)
  b,live,writes=self.bridge(state,today=20260513);requests=[(1,2,0,0,0,20260513)]
  b.scan=lambda:requests
  with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'),patch.object(r,'decide_loan') as decide:
   b.tick();self.assertFalse(b.finance_enabled());self.assertFalse(writes)
   requests.clear();b.tick();decide.assert_not_called()
   requests.append((2,2,0,1,0,20260513));b.last_scan=0;b.tick();self.assertTrue(b.finance_enabled());self.assertEqual(b.finance_ack,2)
   self.assertFalse(writes)
 def test_loan_collection_switch_retains_debt_and_reenable_collects_once(self):
  ctx=context(20260411);state,_,_=f.apply(empty(1043,20260411),club=1043,today=20260411,budget=10_000_000,context=ctx)
  state,budget,_=borrow(state,request_id='loan',club=1043,today=20260411,budget=10_000_000,bank=0,amount=1_000_000,months=12)
  state=f.toggle(state,'loans',False,20260411);b,live,writes=self.bridge(state,today=20260611,budget=budget);requests=[];b.scan=lambda:requests
  with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'):
   b.tick();self.assertEqual(b.state['contracts'][0]['paid'],0);self.assertFalse(writes)
   requests.append((1,2,4,1,0,20260611));b.last_scan=0;b.tick();requests.clear()
   b.tick();self.assertEqual(b.state['contracts'][0]['paid'],2);self.assertEqual(len(writes),1)
   b.tick();self.assertEqual(len(writes),1)
 def test_old_save_checkpoint_does_not_adopt_future_zero_delta_finance_journal(self):
  state,_,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=10_000_000,context=context())
  state,_,_=f.apply(state,club=1043,today=20260601,budget=0,context=context(20260601))
  old=empty(1043,20260511);journal=dict(status='request_registered',source_save_hash='hash',session='old',before=dict(club=1043),state_after=state)
  actual=r.recover_pending(old,dict(club=1043,date=20260511),journal,'new',{},'hash')
  self.assertEqual(actual,old)
 def test_finance_ready_is_session_scoped_and_still_renewed_when_data_did_not_change(self):
  b,live,_=self.bridge(empty(1043,20260511));b.club=1043;b.save=dict(process_created_100ns=444)
  profile=dict(club_id=1043,context_address=b.context_address,context_epoch=3,registry_address=123)
  with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'competition_session',return_value=profile),patch('prepared_views.publish') as ready:
   b.publish_finance_ready(live,'a'*64);b.publish_finance_ready(live,'a'*64)
   self.assertEqual(ready.call_count,2)
   self.assertEqual(ready.call_args.args[1],dict(pid=1,process_created_100ns=444))
   for key in ('club_id','context_address','context_epoch'):
    bad=dict(profile);bad[key]+=1
    with patch.object(r,'competition_session',return_value=bad),self.assertRaises(ValueError):b.publish_finance_ready(live,'a'*64)
   self.assertEqual(ready.call_count,2)
 def test_setting_publishes_confirmation_on_same_tick_and_never_writes_budget(self):
  state,_,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=10_000_000,context=context())
  b,live,writes=self.bridge(state);b.finance_reader=object();b.scan=lambda:[(1,2,1,0,0,20260511)]
  with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'),patch.object(b,'publish_club_finance') as publish:
   b.tick();publish.assert_called_once_with(live)
   self.assertEqual(b.finance_result,dict(sequence=1,ok=True,message='Configuração aplicada.'))
   self.assertFalse(b.state['finance']['settings']['tv']);self.assertFalse(writes)

if __name__=='__main__':unittest.main()
