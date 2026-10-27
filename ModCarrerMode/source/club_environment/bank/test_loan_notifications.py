import json,tempfile,unittest
from pathlib import Path
from loans import empty,borrow
from loan_notifications import make_notice,record,dispatch
from runtime import recover_pending


class LoanNotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name);self.out=self.folder/'out';self.out.mkdir()
        self.live=dict(club=1629,date=20261231,budget=20_000_000,address=0x1234,context_epoch=7)
        self.state,self.budget,_=borrow(empty(1629,20261231),request_id='request1',club=1629,today=20261231,budget=20_000_000,bank=0,amount=1_000_000,months=12)
    def notice(self,approved=True):
        return make_notice('request1',self.live,approved=approved,bank=0,amount=1_000_000,
                           budget_after=self.budget if approved else self.live['budget'],message='Resultado',contract=self.state['contracts'][0] if approved else None)
    def send(self,state=None):dispatch(self.folder,self.out,self.live,pid=123,context=0x1000,state=self.state if state is None else state)
    def test_next_career_day_year_rollover_and_budget_details(self):
        n=self.notice();self.assertEqual(n['due'],20270101);self.assertIn('20.000.000',n['body']);self.assertIn('21.000.000',n['body']);self.assertIn('31/01/2027',n['body'])
        record(self.folder,n);record(self.folder,n);self.send();self.assertFalse((self.out/'native_mail_request.tsv').exists())
        self.live['date']=20270103;self.send();payload=(self.out/'native_mail_request.tsv').read_text();self.assertIn('epoch=7',payload)
        self.assertEqual(len(json.loads((self.folder/'notifications.json').read_text())),1)
    def test_native_receipt_marks_once_and_loading_preloan_save_cancels_queue(self):
        n=self.notice();record(self.folder,n);self.live['date']=20270101;self.send()
        self.send(empty(1629,20261231));self.assertFalse((self.out/'native_mail_request.tsv').exists())
        self.send();(self.out/'native_mail_receipt.tsv').write_text(f"pid=123\nclub=1629\ncontext=1000\nepoch=7\nid={n['id']}\ndate=20270101\n")
        self.send();self.assertTrue(json.loads((self.folder/'notifications.json').read_text())[0]['delivered']);self.assertFalse((self.out/'native_mail_request.tsv').exists())
        self.live['context_epoch']=8;self.send();self.assertTrue((self.out/'native_mail_request.tsv').exists())
    def test_refusal_does_not_require_or_create_a_debt(self):
        n=self.notice(False);record(self.folder,n);self.live['date']=20270101;state=empty(1629,20261231);self.send(state)
        self.assertFalse(state['contracts']);self.assertIn('Nenhum crédito',n['body']);self.assertIn('20.000.000',n['body']);self.assertNotIn('21.000.000',n['body'])
    def test_restart_recovers_debt_but_never_replays_credit_or_a_newer_load(self):
        before=dict(self.live);current=dict(before,budget=self.budget);old=empty(1629,20261231)
        journal=dict(session='session',before=before,after_budget=self.budget,state_after=self.state,status='prepared',native_io_tick=10)
        io=dict(operation='read',access_tick_ms=10)
        self.assertEqual(recover_pending(old,current,journal,'session',io),self.state)
        self.assertIs(recover_pending(old,current,journal,'other',io),old)
        self.assertIs(recover_pending(old,current,journal,'session',dict(operation='read',access_tick_ms=11)),old)
        self.assertIs(recover_pending(old,before,journal,'session',io),old)
        with self.assertRaises(RuntimeError):recover_pending(old,dict(current,budget=19),journal,'session',io)

if __name__=='__main__':unittest.main()
