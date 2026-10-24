"""Regressions for loans requested before leaving the screen/calendar jumps."""
import ctypes,json,tempfile,unittest,threading
from pathlib import Path
from unittest.mock import patch
import loans as l
import runtime as r
import loan_notifications as mail
import save_sidecar as sql
from test_finance_live_ui import open_screen,text
from bank_design import ORDER


class BackgroundLoanTests(unittest.TestCase):
    def test_request_then_decision_run_on_central_without_revisiting_loans(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'):
            b=r.Bridge.__new__(r.Bridge);b.apply=True;b.state=l.empty(1043,20260111)
            b.session='test';b.scope='scope';b.io_tick=1;b.saved_hash='hash';b.result=None
            b.process=type('P',(),{'pid':1})();b.context_address=0x1000;b.write_handle=1;b.nonce='BACKGROUND'
            b.last_sequence=0;b.last_scan=0;b.last_advance=(None,None);b.last_bank_seen=-10000
            live=dict(club=1043,date=20260111,budget=28_000_000,address=0x1234,
                page='game/screens/fluxHub/FluxHub',context_epoch=3)
            b.live=lambda:dict(live);b.observe_save=lambda:None
            b.scan=lambda:[(1,0,9,2,1,20260111)]
            observed=[]
            def screen(_):
                payload=(Path(folder)/'native_mail_request.tsv').read_text()
                observed.append(dict(line.split('=',1) for line in payload.splitlines() if '=' in line))
            b.publish_view=screen;writes=[]
            class Kernel:
                def WriteProcessMemory(self,handle,address,buffer,size,written):
                    live['budget']=int.from_bytes(ctypes.string_at(buffer,size),'little');writes.append(live['budget'])
                    ctypes.cast(written,ctypes.POINTER(ctypes.c_size_t))[0]=4;return True
            b.memory=type('Memory',(),{'kernel32':Kernel(),'read_uint32':lambda _,at:live['budget']})()
            b.tick()
            self.assertEqual(b.state['application']['date'],20260111)
            self.assertEqual(observed[0]['due'],'20260111')
            self.assertFalse(writes)
            first=observed[0]
            (Path(folder)/'native_mail_receipt.tsv').write_text(f"pid=1\nclub=1043\ncontext=1000\nepoch=3\nid={first['id']}\ndate=20260111\n")
            # Jump directly past the decision date, never entering Loans.
            live['date']=20260114;b.tick();b.tick()
            self.assertEqual(writes,[33_000_000])
            self.assertEqual(observed[-1]['due'],'20260112')
            self.assertEqual(b.state['applications'][0]['date'],20260111)
            self.assertEqual(b.state['applications'][0]['decision_date'],20260112)
            self.assertEqual(b.state['applications'][0]['decided_date'],20260114)

    def test_reader_only_opens_a_read_handle_and_discovers_without_a_screen(self):
        calls=[];finished=threading.Event()
        class Kernel:
            def OpenProcess(self,access,inherit,pid):calls.append(('open',access,pid));return 1
        class Memory:
            kernel32=Kernel()
            def close(self):calls.append(('closed',));finished.set()
        process=type('P',(),{'pid':777,'is_running':lambda _:True})()
        def scan(scanner):
            self.assertEqual(scanner.nonce,'READ_ONLY')
            return [(1,0,9,0,1,20260111)]
        with patch.object(r,'Memory',Memory),patch.object(r.Bridge,'scan_bounded',scan):
            reader=r.RequestReader(process,0x140000000,'READ_ONLY')
            try:
                rows=[]
                for _ in range(100):
                    rows+=reader.read()
                    if rows:break
                    finished.wait(.01)
                self.assertEqual(rows,[(1,0,9,0,1,20260111)])
                self.assertFalse(reader.read())
            finally:reader.close()
        self.assertEqual(calls,[('open',0x410,777),('closed',)])
        self.assertFalse(reader.thread.is_alive())

    def test_bank_deadlines_vary_and_pending_proposals_never_slide(self):
        deadlines=[]
        for bank,days in ((9,1),(7,2),(3,3),(8,4)):
            state,budget,_=l.request_loan(l.empty(1043,20261230),request_id=str(bank),club=1043,
                today=20261230,budget=28_000_000,bank=bank,amount=1_000_000,months=12)
            expected=int((l.parse_date(20261230)+l.timedelta(days=days)).strftime('%Y%m%d'))
            self.assertEqual(state['application']['decision_date'],expected);deadlines.append(expected)
            state,budget,_=l.advance(state,club=1043,today=20270104,budget=budget)
            self.assertEqual(state['application']['date'],20261230)
            self.assertEqual(state['application']['decision_date'],expected)
        self.assertEqual(len(set(deadlines)),4)

    def test_catalog_calibration_preserves_custom_sql_and_frozen_contracts(self):
        with tempfile.TemporaryDirectory() as folder:
            save=Path(folder)/'DATA';save.write_bytes(b'untouched')
            with sql.connection(save) as db:
                db.execute("DELETE FROM bank_catalog_settings WHERE key='reference_rates_20261024'")
                db.execute("UPDATE bank_catalog SET rate_bps=80 WHERE slug='bb'")
                db.execute("UPDATE bank_catalog SET rate_bps=333 WHERE slug='itau'")
            rows={slug:bps for _,slug,_,bps in sql.bank_rows(save)}
            self.assertEqual(rows['bb'],205);self.assertEqual(rows['itau'],333)
            with sql.connection(save) as db:db.execute("UPDATE bank_catalog SET rate_bps=80 WHERE slug='bb'")
            self.assertEqual({slug:bps for _,slug,_,bps in sql.bank_rows(save)}['bb'],80)
            self.assertEqual(save.read_bytes(),b'untouched')

    def test_native_proposal_shows_only_count_and_selected_bank_deadline(self):
        view=l.presentation(l.empty(1043,20260111),20260111,28_000_000,ready=True,nonce='DESIGN')
        vm,screen,_=open_screen(view)
        self.assertEqual(text(screen,'subtitle'),'0/2 empréstimos em 2026')
        for bank,expected in ((9,'12/01/2026'),(7,'13/01/2026'),(3,'14/01/2026'),(8,'15/01/2026')):
            screen.set('page',1);screen.set('focus',ORDER.index(bank));vm.invoke(screen.get('Refresh'),screen)
            self.assertEqual(text(screen,'summaryValue3'),expected)
            self.assertEqual(text(screen,'responseHint'),'')
            screen.set('page',2);vm.invoke(screen.get('Refresh'),screen)
            self.assertEqual(text(screen,'detail4'),'Resposta prevista: '+expected)


if __name__=='__main__':unittest.main()
