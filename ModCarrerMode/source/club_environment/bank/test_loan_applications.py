import unittest,ctypes,tempfile,json
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import loans as l
import runtime as r


class ApplicationTests(unittest.TestCase):
 def request(self,state=None,**changes):
  args=dict(request_id='application',club=1629,today=20260131,budget=20_000_000,bank=0,amount=1_000_000,months=12)
  args.update(changes)
  return l.request_loan(state or l.empty(1629,20260131),**args)

 def test_submission_has_no_credit_and_decision_uses_next_day_budget(self):
  state,budget,events=self.request()
  self.assertEqual(budget,20_000_000);self.assertFalse(state['contracts'])
  self.assertEqual(state['application']['decision_date'],20260201)
  self.assertFalse(l.presentation(state,20260131,budget)['can_borrow'])
  before=deepcopy(state)
  repeated,b2,e=self.request(state);self.assertEqual((repeated,b2,e),(state,budget,[]))
  with self.assertRaises(ValueError):self.request(state,request_id='duplicate')
  waiting,b2,e,decision=l.decide_loan(state,club=1629,today=20260131,budget=18_000_000)
  self.assertIsNone(decision);self.assertEqual(b2,18_000_000)
  approved,b2,e,decision=l.decide_loan(state,club=1629,today=20260201,budget=18_000_000)
  self.assertTrue(decision['approved']);self.assertEqual(b2,19_000_000)
  self.assertEqual(approved['contracts'][0]['payments'][0]['date'],20260301)
  self.assertNotIn('application',approved);self.assertEqual(state,before)
  repeated,b3,e,decision=l.decide_loan(approved,club=1629,today=20260201,budget=b2)
  self.assertEqual(b3,b2);self.assertFalse(e);self.assertIsNone(decision)

 def test_later_day_refusal_clears_request_without_credit(self):
  state,_,_=self.request()
  refused,budget,events,response=l.decide_loan(state,club=1629,today=20260204,budget=l.MAX_BUDGET)
  self.assertFalse(response['approved']);self.assertNotIn('application',refused)
  self.assertEqual(budget,l.MAX_BUDGET);self.assertFalse(refused['contracts'])
  self.assertEqual(events[0]['event'],'application_refused')

 def test_delayed_request_keeps_submission_and_response_dates(self):
  state,budget,_=self.request(l.empty(1629,20260204),today=20260204,submitted_on=20260131)
  self.assertEqual(state['application']['date'],20260131)
  self.assertEqual(state['application']['decision_date'],20260201)
  self.assertEqual(state['application']['registered_date'],20260204)
  state,budget,_,decision=l.decide_loan(state,club=1629,today=20260204,budget=budget)
  self.assertEqual(decision['decision_date'],20260201);self.assertEqual(decision['decided_date'],20260204)
  self.assertEqual(state['applications'][0]['date'],20260131)
  self.assertEqual(state['applications'][0]['decision_date'],20260201)
  self.assertEqual(state['applications'][0]['status'],'approved')
  for today in (20260205,20260206,20260220):
   state,budget,_=l.advance(state,club=1629,today=today,budget=budget)
   self.assertEqual(l.presentation(state,today,budget)['last_decision']['decision_date'],20260201)

 def test_request_transport_carries_click_date_in_ascii_and_utf16(self):
  message='S16BANK_V3|TEST|9|0|2|1|1|20260126|END_S16BANK'
  for encoding in ('ascii','utf-16-le'):
   self.assertEqual(r.requests_in(message.encode(encoding),'TEST'),{(9,0,2,1,1,20260126)})
  self.assertFalse(r.requests_in(message.replace('20260126','20261326').encode(),'TEST'))
  self.assertFalse(r.requests_in(message.encode(),'OTHER'))

 def test_application_journal_restores_without_replaying_credit(self):
  state,budget,_=self.request()
  before=dict(club=1629,budget=budget,address=123,date=20260131)
  journal=dict(status='request_registered',session='old',source_save_hash='same-save',native_io_tick=5,before=before,state_after=state)
  clean=l.empty(1629,20260131);live=dict(before,date=20260201)
  self.assertEqual(r.recover_pending(clean,live,journal,'new',{},'same-save'),state)
  self.assertEqual(r.recover_pending(clean,live,journal,'new',{},'other-save'),clean)
  self.assertEqual(r.recover_pending(clean,dict(live,club=1043),journal,'new',{},'same-save'),clean)
  self.assertEqual(r.recover_pending(clean,live,journal,'old',{'operation':'read','access_tick_ms':6},'same-save'),clean)

 def test_request_publication_never_writes_budget(self):
  state,budget,events=self.request()
  b=r.Bridge.__new__(r.Bridge);b.apply=True;b.state=l.empty(1629,20260131)
  b.session='test';b.scope='test';b.io_tick=5;b.saved_hash='hash';b.result=None
  shown=[];b.flush_notifications=lambda live:shown.append(live)
  b.publish_view=lambda _:self.fail('Rendering delayed the receipt')
  before=dict(club=1629,date=20260131,budget=budget)
  with patch.object(r,'write_json') as write,patch.object(r,'log'):
   b.publish(before,state,budget,events,'loan_requested',{'ok':True,'kind':'loan_requested'})
   self.assertEqual(write.call_args.args[1]['status'],'request_registered')
  self.assertEqual(b.state,state);self.assertEqual(shown,[before])

 def test_worker_day_change_credits_once_queues_inbox_and_debits_monthly(self):
  b=r.Bridge.__new__(r.Bridge);b.apply=True;b.state=l.empty(1629,20260131)
  b.session='test';b.scope='test';b.io_tick=5;b.saved_hash='hash';b.result=None
  b.process=type('P',(),{'pid':123})();b.context_address=0x1000;b.write_handle=1
  b.nonce='TEST';b.last_sequence=0;b.last_scan=0;b.last_advance=(None,None)
  live=dict(club=1629,date=20260131,budget=20_000_000,address=0x1234,page=r.PAGE,context_epoch=7)
  b.live=lambda:dict(live);b.observe_save=lambda:None;b.publish_view=lambda _:None
  b.scan=lambda:[(1,0,0,0,1)]
  writes=[]
  class Kernel:
   def WriteProcessMemory(self,handle,address,buffer,size,written):
    live['budget']=int.from_bytes(ctypes.string_at(buffer,size),'little');writes.append(live['budget'])
    ctypes.cast(written,ctypes.POINTER(ctypes.c_size_t))[0]=4;return True
  b.memory=type('Memory',(),{'kernel32':Kernel(),'read_uint32':lambda _,at:live['budget']})()
  with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'):
   b.tick();self.assertFalse(writes);self.assertEqual(b.result['kind'],'loan_requested')
   self.assertTrue((Path(folder)/'native_mail_request.tsv').exists())
   first=json.loads((Path(folder)/'test/notifications.json').read_text(encoding='utf8'))
   self.assertEqual([n['kind'] for n in first],['application'])
   live.update(date=20260201,page='game/screens/fluxhub/fluxhub');b.tick()
   self.assertEqual(writes,[21_000_000]);self.assertEqual(b.result['kind'],'loan_decision')
   notice=next(n for n in json.loads((Path(folder)/'test/notifications.json').read_text(encoding='utf8')) if n.get('kind')=='decision')
   self.assertEqual(notice['due'],20260201);self.assertIn('20.000.000',notice['body']);self.assertIn('21.000.000',notice['body'])
   self.assertTrue((Path(folder)/'native_mail_request.tsv').exists())
   b.tick();self.assertEqual(writes,[21_000_000])
   installment=b.state['contracts'][0]['payments'][0]['amount']
   live['date']=20260301;b.tick();b.tick()
   self.assertEqual(writes,[21_000_000,21_000_000-installment]);self.assertEqual(b.state['contracts'][0]['paid'],1)

 def test_memory_inventory_refresh_does_not_restart_large_heap_scan(self):
  b=r.Bridge.__new__(r.Bridge);b.nonce='TEST';b.last_sequence=0;b.inventory_time=0
  b.scan_inventory=[(0x10000,1024**3)];b.scan_cursor=0;b.scan_offset=10*1024**2
  b.priority_chunks=[];reads=[]
  class Query:
   def __call__(self,handle,address,out,size):
    if address!=0x10000:return 0
    info=ctypes.cast(out,ctypes.POINTER(r.Region))[0]
    info.base=0x10000;info.size=1024**3;info.state=0x1000;info.type=0x20000;info.protect=4
    return size
  def read(at,size):reads.append(at);return b''
  b.memory=type('Memory',(),{'kernel32':type('Kernel',(),{'VirtualQueryEx':Query()})(),'process_handle':1,'read_process_memory':staticmethod(read)})()
  with patch.object(r.time,'monotonic',return_value=20):b.scan_bounded()
  self.assertEqual(reads[0],0x10000+10*1024**2)

if __name__=='__main__':unittest.main(verbosity=2)
