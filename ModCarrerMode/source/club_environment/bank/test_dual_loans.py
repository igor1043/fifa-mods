"""Two independent debts, scoped payments and skipped-calendar catch-up."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import ctypes,json,tempfile,unittest
import loans as l
import loan_notifications as mail
import runtime as r
from test_finance_live_ui import open_screen,text
from bank_design import ORDER,N


class DualLoanTests(unittest.TestCase):
    def pair(self):
        state,budget,_=l.borrow(l.empty(1043,20260108),request_id='one',club=1043,
            today=20260108,budget=28_000_000,bank=9,amount=3_000_000,months=12)
        # Imported historical debts may predate the new spacing rule.
        with patch.object(l,'borrowing_date',return_value=0):
            state,budget,_=l.borrow(state,request_id='two',club=1043,
                today=20260110,budget=budget,bank=3,amount=5_000_000,months=24)
        return state,budget

    def test_historical_dual_debt_is_retained_but_new_requests_wait_two_months(self):
        state,budget=self.pair()
        self.assertEqual(len(state['contracts']),2)
        self.assertEqual(budget,36_000_000)
        self.assertEqual(l.presentation(state,20260110,budget)['active_count'],2)
        self.assertFalse(l.presentation(state,20260110,budget)['can_borrow'])
        with self.assertRaisesRegex(ValueError,'dois meses'):
            l.borrow(state,request_id='third',club=1043,today=20260110,budget=budget,bank=3,amount=1_000_000,months=12)
        paid,budget,_=l.pay(state,request_id='settle-one',club=1043,today=20260110,budget=budget,settle=True,contract_id='one')
        with self.assertRaisesRegex(ValueError,'dois meses'):
            l.borrow(paid,request_id='third',club=1043,today=20260110,budget=budget,bank=3,amount=1_000_000,months=12)

    def test_second_request_decision_is_separate_and_never_reprices_the_frozen_offer(self):
        state,budget=self.pair();state['contracts'].pop()
        state['processed'].remove('two');budget-=5_000_000
        self.assertTrue(l.presentation(state,20260308,budget)['can_borrow'])
        pending,_,_=l.request_loan(state,request_id='application-two',club=1043,today=20260308,
            budget=budget,bank=3,amount=20_000_000,months=36)
        frozen=deepcopy(pending['application']['quote'])
        with patch.dict(l.BANKS[3],rate_bps=700):
            approved,after,_,decision=l.decide_loan(pending,club=1043,today=pending['application']['decision_date'],budget=budget)
        self.assertTrue(decision['approved'])
        self.assertEqual(after,budget+20_000_000)
        self.assertEqual(approved['contracts'][1]['rate_bps'],frozen['rate_bps'])
        self.assertEqual(approved['contracts'][0],state['contracts'][0])

    def test_manual_payment_and_settlement_only_change_the_selected_contract(self):
        state,budget=self.pair();before=deepcopy(state)
        with self.assertRaisesRegex(ValueError,'Selecione o contrato'):
            l.pay(state,request_id='ambiguous',club=1043,today=20260110,budget=budget)
        updated,after,events=l.pay(state,request_id='pay-two',club=1043,today=20260110,budget=budget,contract_id='two')
        self.assertEqual(updated['contracts'][0],before['contracts'][0])
        self.assertEqual(updated['contracts'][1]['paid'],1)
        self.assertEqual(after,budget-before['contracts'][1]['payments'][0]['amount'])
        self.assertEqual(events[0]['id'],'two')
        repeated,again,events=l.pay(updated,request_id='pay-two',club=1043,today=20260110,budget=after,contract_id='two')
        self.assertEqual((repeated,again,events),(updated,after,[]))
        settled,last,events=l.pay(updated,request_id='settle-two',club=1043,today=20260110,budget=after,contract_id='two',settle=True)
        self.assertEqual(settled['contracts'][0]['paid'],0)
        self.assertEqual(settled['contracts'][1]['paid'],24)
        self.assertEqual({e['id'] for e in events},{'two'})
        with self.assertRaises(ValueError):
            l.pay(settled,request_id='stale',club=1043,today=20260110,budget=last,contract_id='two')
        self.assertEqual(state,before)

    def test_calendar_jump_collects_every_due_installment_of_both_debts_once(self):
        state,budget=self.pair()
        after,remaining,events=l.advance(state,club=1043,today=20260415,budget=budget)
        expected=sum(p['amount'] for c in state['contracts'] for p in c['payments'] if p['date']<=20260415)
        self.assertEqual(budget-remaining,expected)
        self.assertEqual([c['paid'] for c in after['contracts']],[3,3])
        self.assertEqual(len(events),6)
        self.assertTrue(all(e['paid_date']==20260415 and e['date']<20260415 for e in events))
        repeated,same,events=l.advance(after,club=1043,today=20260415,budget=remaining)
        self.assertEqual((repeated,same,events),(after,remaining,[]))
        later,same,events=l.advance(after,club=1043,today=20260420,budget=remaining)
        self.assertEqual(same,remaining);self.assertFalse(events)

    def test_insufficient_budget_keeps_due_debt_and_retries_when_money_arrives(self):
        state,budget=self.pair();first=state['contracts'][0]['payments'][0]['amount']
        late,left,events=l.advance(state,club=1043,today=20260415,budget=first)
        self.assertEqual(left,0);self.assertEqual([c['paid'] for c in late['contracts']],[1,0])
        self.assertTrue(any(e['event']=='arrears' for e in events))
        caught,after,events=l.advance(late,club=1043,today=20260415,budget=20_000_000)
        self.assertEqual([c['paid'] for c in caught['contracts']],[3,3])
        self.assertEqual(sum(e['event']=='installment' for e in events),5)
        self.assertGreaterEqual(after,0)

    def test_calendar_jump_past_both_maturities_settles_all_without_repeating_credit_or_debits(self):
        state,budget=self.pair()
        after,remaining,events=l.advance(state,club=1043,today=20290101,budget=budget)
        self.assertEqual(budget-remaining,sum(c['total'] for c in state['contracts']))
        self.assertEqual(len(events),36)
        self.assertFalse(l.presentation(after,20290101,remaining)['active_contracts'])
        self.assertTrue(l.presentation(after,20290101,remaining)['can_borrow'])
        repeated,same,events=l.advance(after,club=1043,today=20290101,budget=remaining)
        self.assertEqual((repeated,same,events),(after,remaining,[]))

    def test_worker_calendar_jump_writes_once_then_restores_paid_state_without_replaying(self):
        for page in ('game/screens/career/calendar','game/screens/fluxhub/fluxhub'):
            with self.subTest(page=page),tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)),patch.object(r,'log'),patch.object(r.time,'sleep'):
                state,budget=self.pair();b=r.Bridge.__new__(r.Bridge)
                b.apply=True;b.state=state;b.session='dual';b.scope='scope';b.io_tick=10;b.saved_hash='hash';b.result=None
                b.process=type('P',(),{'pid':100})();b.context_address=0x1000;b.write_handle=1;b.nonce='DUAL'
                b.last_sequence=0;b.last_scan=0;b.last_advance=(None,None)
                live=dict(club=1043,date=20260415,budget=budget,address=0x1234,page=page,context_epoch=9)
                b.live=lambda:dict(live);b.observe_save=lambda:None;b.publish_view=lambda _:None;b.scan=lambda:[]
                writes=[]
                class Kernel:
                    def WriteProcessMemory(self,handle,address,buffer,size,written):
                        live['budget']=int.from_bytes(ctypes.string_at(buffer,size),'little');writes.append(live['budget'])
                        ctypes.cast(written,ctypes.POINTER(ctypes.c_size_t))[0]=4;return True
                b.memory=type('Memory',(),{'kernel32':Kernel(),'read_uint32':lambda _,at:live['budget']})()
                b.tick();b.tick();self.assertEqual(len(writes),1)
                self.assertEqual([c['paid'] for c in b.state['contracts']],[3,3])
                journal=json.loads((Path(folder)/'scope/pending.json').read_text(encoding='utf8'))
                recovered=r.recover_pending(state,live,journal,'dual',dict(operation='read',access_tick_ms=10))
                self.assertEqual(recovered,b.state)
                b.state=recovered;b.last_advance=(None,None);b.tick();self.assertEqual(len(writes),1)
                rows=json.loads((Path(folder)/'scope/notifications.json').read_text(encoding='utf8'))
                self.assertEqual(sum(n['kind']=='payment' for n in rows),2)
                for notice in (n for n in rows if n['kind']=='payment'):
                    self.assertIn('Pagamento aplicado em: 15/04/2026',notice['body'])
                    self.assertIn('Vencimentos cobrados: ',notice['body'])
                    self.assertIn('04/2026',notice['body'])
                # A skipped D-1 is not emitted later as a false "tomorrow" alert.
                queued=(Path(folder)/'native_mail_request.tsv').read_text(encoding='ascii')
                self.assertNotIn('vence amanhã'.encode('utf8').hex(),queued)

    def test_v4_wire_transports_contract_id_in_ascii_and_utf16_and_rejects_bad_indexes(self):
        target='B57_12345_1043_abcc2e7a01a9:123456'
        request=f'S16BANK_V4|DUAL|7|2|10|8|4|20260211|{target}|END_S16BANK'
        for encoding in ('ascii','utf-16-le'):
            self.assertEqual(r.requests_in(request.encode(encoding),'DUAL'),{(7,2,10,8,4,20260211,target)})
            for invalid in (request.replace('|10|8|4|','|10|99|4|'),request.replace('|2|10|','|0|10|'),request.replace('|20260211|','|20260230|')):
                self.assertFalse(r.requests_in(invalid.encode(encoding),'DUAL'))
        self.assertFalse(r.requests_in(request.encode(),'OTHER'))

    def test_native_footer_left_right_moves_between_actions_up_returns_to_table_and_no_auto_payment(self):
        state,budget=self.pair();view=l.presentation(state,20260110,budget,ready=True,nonce='DUAL_UI',club_name='Flamengo')
        vm,screen,_=open_screen(view)
        screen.set('page',7);screen.set('contractIndex',0);screen.set('focus',2);vm.invoke(screen.get('Refresh'),screen)
        vm.invoke(screen.get('LocalEventHandler'),screen,[6]);self.assertEqual(screen.get('focus'),3)
        vm.invoke(screen.get('LocalEventHandler'),screen,[5]);self.assertEqual(screen.get('focus'),2)
        vm.invoke(screen.get('MoveFocus'),screen,[1]);self.assertEqual(screen.get('focus'),2)
        screen.set('focus',0);vm.invoke(screen.get('Refresh'),screen);vm.invoke(screen.get('Select'),screen)
        self.assertEqual(screen.get('page'),3);self.assertIn('Banco do Brasil',text(screen,'statementHeading'))
        screen.set('focus',23);vm.invoke(screen.get('Refresh'),screen)
        vm.invoke(screen.get('MoveFocus'),screen,[1]);self.assertEqual(screen.get('focus'),24)
        vm.invoke(screen.get('LocalEventHandler'),screen,[6]);self.assertEqual(screen.get('focus'),25)
        vm.invoke(screen.get('LocalEventHandler'),screen,[6]);self.assertEqual(screen.get('focus'),26)
        vm.invoke(screen.get('LocalEventHandler'),screen,[5]);self.assertEqual(screen.get('focus'),25)
        vm.invoke(screen.get('MoveFocus'),screen,[1]);self.assertEqual(screen.get('focus'),25)
        vm.invoke(screen.get('MoveFocus'),screen,[-1]);self.assertEqual(screen.get('focus'),23)
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

    def test_native_payment_confirmation_and_request_reference_the_selected_second_contract(self):
        state,budget=self.pair();view=l.presentation(state,20260110,budget,ready=True,nonce='PAY_DUAL')
        vm,screen,_=open_screen(view)
        screen.set('page',7);screen.set('focus',0);vm.invoke(screen.get('Refresh'),screen);vm.invoke(screen.get('Select'),screen)
        screen.set('focus',24);vm.invoke(screen.get('Refresh'),screen);vm.invoke(screen.get('Select'),screen)
        self.assertEqual(screen.get('page'),4)
        self.assertEqual(screen.get('selectedPaymentId'),'two')
        self.assertIn('Banco do Brasil',text(screen,'detail0'))
        self.assertIn(mail.money(state['contracts'][1]['payments'][0]['amount']),text(screen,'detail2'))
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
        vm.invoke(screen.get('Select'),screen)
        wire=vm.global_.get('Server16BankRequestV2')
        received=next(iter(r.requests_in(wire.encode(),'PAY_DUAL')))
        self.assertEqual(received[1],1);self.assertEqual(received[6],'two')


class OfferProductTests(unittest.TestCase):
    def test_bank_limits_differ_and_amount_and_term_raise_the_quoted_interest(self):
        limits={l.product_limits(bank) for bank in l.OFFERED_BANKS}
        self.assertGreaterEqual(len(limits),5)
        for bank in l.OFFERED_BANKS:
            rates=[]
            for ai in l.amount_indices(bank):
                amount=l.AMOUNTS[ai];q=l.quote(bank,amount,12);rates.append(q['rate_bps'])
                self.assertEqual(sum(p['principal'] for p in q['payments']),amount)
                self.assertEqual(q['payments'][-1]['balance'],0)
            self.assertEqual(rates,sorted(rates));self.assertGreater(rates[-1],rates[0])
            short=l.quote(bank,1_000_000,6);long=l.quote(bank,1_000_000,l.product_limits(bank)[1])
            self.assertGreater(long['rate_bps'],short['rate_bps'])
            self.assertGreater(long['total'],short['total'])
        with self.assertRaises(ValueError):l.quote(5,100_000_000,48)
        large=l.quote(10,100_000_000,48)
        self.assertGreaterEqual(large['rate_bps'],400)

    def test_native_bank_switch_clamps_unsupported_values_and_shows_the_actual_tier_rate(self):
        view=l.presentation(l.empty(1043,20260110),20260110,28_000_000,ready=True,nonce='PRODUCT_UI')
        vm,screen,_=open_screen(view)
        screen.set('page',1);screen.set('focus',ORDER.index(10));screen.set('amountIndex',8);screen.set('termIndex',4)
        vm.invoke(screen.get('Refresh'),screen)
        self.assertIn('100.000.000',screen.get('amountControl').get('label').get('text'))
        self.assertEqual(text(screen,'summaryValue9'),'5,95% ao mês')
        self.assertIn('48 meses',screen.get('termControl').get('label').get('text'))
        screen.set('focus',ORDER.index(5));vm.invoke(screen.get('Refresh'),screen)
        self.assertEqual(l.AMOUNTS[screen.get('amountIndex')],10_000_000)
        self.assertEqual(l.TERMS[screen.get('termIndex')],24)
        for _ in range(12):
            screen.set('focus',N);vm.invoke(screen.get('Shift'),screen,[1])
            self.assertIn(screen.get('amountIndex'),l.amount_indices(5))
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

    def test_large_offer_simulation_scrolls_to_installment_48_without_requesting_credit(self):
        view=l.presentation(l.empty(1043,20260110),20260110,28_000_000,ready=True,nonce='PLAN48')
        vm,screen,_=open_screen(view)
        screen.set('page',1);screen.set('focus',ORDER.index(10));screen.set('amountIndex',8);screen.set('termIndex',4)
        vm.invoke(screen.get('Refresh'),screen)
        screen.set('focus',N+2);vm.invoke(screen.get('Select'),screen)
        screen.set('focus',2);vm.invoke(screen.get('Select'),screen)
        self.assertEqual(screen.get('page'),6)
        for _ in range(7):vm.invoke(screen.get('LocalEventHandler'),screen,[6])
        self.assertEqual(screen.get('statementPage'),7)
        self.assertEqual(text(screen,'cell1_0'),'43')
        self.assertEqual(text(screen,'cell6_0'),'48')
        self.assertIn('2030',text(screen,'cell6_1'))
        self.assertTrue(screen.get('tableHeader').get('_visible'))
        self.assertEqual(screen.get('cell1_0').get('_y'),395)
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))


if __name__=='__main__':unittest.main()
