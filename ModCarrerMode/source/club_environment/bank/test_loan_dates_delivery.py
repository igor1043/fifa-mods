"""Regressions for immutable request dates, SQL and the real inbox transport."""
import ctypes,json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import loans as l
import runtime as r
import save_sidecar as sql
import loan_notifications as mail
import bank_ui_r60 as ui
from test_finance_live_ui import open_screen,text
from formats import AptFile,BigFile,Placement


class DatesAndDeliveryTests(unittest.TestCase):
 def request(self):
  return l.request_loan(l.empty(517,20260131),request_id='fixed',club=517,today=20260131,
      budget=20_000_000,bank=9,amount=5_000_000,months=12)

 def test_live_sql_keeps_submission_response_and_credit_status_before_a_native_save(self):
  state,budget,_=self.request()
  with tempfile.TemporaryDirectory() as folder:
   save=Path(folder)/'DATA';save.write_bytes(b'unchanged native save')
   sql.save_session_club(save,'hash','session',10,state,[])
   with sql.connection(save) as db:
    self.assertEqual(db.execute('SELECT submitted_date,response_date,status,credit_applied FROM loan_requests').fetchone(),(20260131,20260201,'pending',0))
   for today in (20260201,20260202,20260203):
    state,budget,_=l.advance(state,club=517,today=today,budget=budget)
    sql.save_session_club(save,'hash','session',10,state,[])
   state,budget,_,_=l.decide_loan(state,club=517,today=20260203,budget=budget)
   sql.save_session_club(save,'hash','session',10,state,[])
   with sql.connection(save) as db:
    self.assertEqual(db.execute('SELECT submitted_date,response_date,status,decided_date,credit_applied FROM loan_requests').fetchone(),(20260131,20260201,'approved',20260203,1))
   changed=deepcopy(state);changed['applications'][0]['decision_date']=20260204
   with self.assertRaises(ValueError):sql.save_session_club(save,'hash','session',10,changed,[])
   self.assertEqual(save.read_bytes(),b'unchanged native save')

 def test_receipt_decision_then_reminder_have_separate_ids_and_native_acknowledgements(self):
  state,budget,_=self.request();state,budget,_,_=l.decide_loan(state,club=517,today=20260201,budget=budget)
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);out=root/'out';out.mkdir();live=dict(club=517,date=20260201,context_epoch=3)
   mail.reconcile(root,state);mail.reconcile(root,state);mail.schedule_reminders(root,state)
   rows=json.loads((root/'notifications.json').read_text(encoding='utf8'))
   self.assertEqual(len(rows),14)
   receipt=next(n for n in rows if n['kind']=='application');decision=next(n for n in rows if n['kind']=='decision')
   self.assertEqual((receipt['due'],decision['due']),(20260131,20260201))
   self.assertIn('31/01/2026',receipt['body']);self.assertIn('01/02/2026',receipt['body'])
   self.assertIn('20.000.000',decision['body']);self.assertIn('25.000.000',decision['body'])
   self.assertNotEqual(receipt['id'],decision['id'])
   def dispatch():mail.dispatch(root,out,live,pid=1,context=0x1000,state=state)
   def ack(n,day):
    (out/'native_mail_receipt.tsv').write_text(f"pid=1\nclub=517\ncontext=1000\nepoch=3\nid={n['id']}\ndate={day}\n",encoding='ascii')
   dispatch();payload=(out/'native_mail_request.tsv').read_text(encoding='ascii')
   self.assertIn('id='+receipt['id'],payload)
   fields=dict(line.split('=',1) for line in payload.splitlines() if '=' in line)
   self.assertEqual(bytes.fromhex(fields['subject']).decode('utf8'),'Empréstimo: pedido recebido')
   ack(receipt,20260201);dispatch();self.assertIn('id='+decision['id'],(out/'native_mail_request.tsv').read_text())
   ack(decision,20260201);dispatch();self.assertFalse((out/'native_mail_request.tsv').exists())
   mail.reconcile(root,state);dispatch();self.assertFalse((out/'native_mail_request.tsv').exists())
   reminder=next(n for n in rows if n.get('kind')=='reminder' and n['number']==1)
   self.assertEqual(reminder['due'],20260228)
   live['date']=20260228;dispatch();self.assertIn('id='+reminder['id'],(out/'native_mail_request.tsv').read_text())
   live['date']=20260301;dispatch();self.assertFalse((out/'native_mail_request.tsv').exists())

 def test_refusal_produces_a_decision_email_without_credit_or_changing_request_dates(self):
  state,budget,_=self.request();state,after,_,_=l.decide_loan(state,club=517,today=20260202,budget=l.MAX_BUDGET)
  self.assertEqual(after,l.MAX_BUDGET);self.assertFalse(state['contracts'])
  with tempfile.TemporaryDirectory() as folder:
   mail.reconcile(folder,state);rows=json.loads((Path(folder)/'notifications.json').read_text(encoding='utf8'))
   self.assertEqual([n['kind'] for n in rows],['application','decision'])
   self.assertEqual(rows[1]['due'],20260201);self.assertIn('Nenhum crédito',rows[1]['body'])

 def test_native_reload_does_not_move_the_dates_while_the_same_click_is_pending(self):
  view=l.presentation(l.empty(517,20260131),20260131,20_000_000,ready=True,nonce='DATES')
  vm,screen,_=open_screen(view);screen.set('page',2);screen.set('focus',0);vm.invoke(screen.get('Select'),screen)
  request=vm.global_.get('Server16BankRequestV2')
  for today in (20260201,20260203,20260205):
   view['date']=today;vm,screen,_=open_screen(view,vm.global_)
   self.assertIn('31/01/2026',text(screen,'detail0'));self.assertIn('02/02/2026',text(screen,'detail6'))
   self.assertEqual(vm.global_.get('Server16BankRequestV2'),request)

 def test_scripted_native_underlays_are_clips_and_can_really_be_hidden(self):
  view=l.presentation(l.empty(517,20260131),20260131,20_000_000,ready=True,nonce='LAYERS')
  open_screen(view);apt=AptFile(BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big'))
  named={p.name:p for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name}
  for name in ('tableHeader','scrollTrack','scrollThumb','ratePanel','summaryCard'):
   self.assertEqual(apt.characters[named[name].character].type,5,name)

 def test_a_click_in_the_warmed_apt_arena_does_not_wait_for_a_whole_heap_sweep(self):
  b=r.Bridge.__new__(r.Bridge);b.nonce='ARENA';b.last_sequence=0;b.inventory_time=20
  b.scan_inventory=[(0x10000,1024**3)];b.scan_cursor=0;b.scan_offset=0
  b.priority_chunks=[(0x20000,512)];b.request_arenas=[(0x100000,6*1024**2)];reads=[]
  def read(address,size):
   reads.append((address,size))
   if address==0x20000:return b'S16BANK_V2|ARENA|0|0|0|0|0|END_S16BANK'
   if address==0x100000:return b'\0'*100+b'S16BANK_V3|ARENA|1|0|9|2|1|20260131|END_S16BANK'
   self.fail('The request should be found before another heap sweep')
  b.memory=type('Memory',(),{'read_process_memory':staticmethod(read),'kernel32':object()})()
  with patch.object(r.time,'monotonic',return_value=20):found=b.scan_bounded()
  self.assertIn((1,0,9,2,1,20260131),found);self.assertEqual(len(reads),2)

 def test_central_calendar_and_loans_apply_the_same_due_decision_exactly_once(self):
  for page in ('game/screens/fluxhub/fluxhub','game/screens/career/calendar',r.PAGE):
   with self.subTest(page=page),tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'):
    state,budget,_=self.request();b=r.Bridge.__new__(r.Bridge)
    b.apply=True;b.state=state;b.session='test';b.scope='scope';b.io_tick=1;b.saved_hash='hash';b.result=None
    b.process=type('P',(),{'pid':1})();b.context_address=0x1000;b.write_handle=1;b.nonce='DATES'
    b.last_sequence=0;b.last_scan=0;b.last_advance=(None,None)
    live=dict(club=517,date=20260201,budget=budget,address=0x1234,page=page,context_epoch=3)
    b.live=lambda:dict(live);b.observe_save=lambda:None;b.publish_view=lambda _:None;b.scan=lambda:[]
    writes=[]
    class Kernel:
     def WriteProcessMemory(self,handle,address,buffer,size,written):
      live['budget']=int.from_bytes(ctypes.string_at(buffer,size),'little');writes.append(live['budget'])
      ctypes.cast(written,ctypes.POINTER(ctypes.c_size_t))[0]=4;return True
    b.memory=type('Memory',(),{'kernel32':Kernel(),'read_uint32':lambda _,at:live['budget']})()
    b.tick();b.tick();self.assertEqual(writes,[25_000_000])
    self.assertEqual(b.state['applications'][0]['decision_date'],20260201)
    self.assertEqual(b.state['applications'][0]['date'],20260131)
    notices=json.loads((Path(folder)/'scope/notifications.json').read_text(encoding='utf8'))
    self.assertEqual(sum(n['kind']=='application' for n in notices),1);self.assertEqual(sum(n['kind']=='decision' for n in notices),1)
