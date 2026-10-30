import json,tempfile,unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import loans as l
import loan_notifications as mail
import save_sidecar as sql
from test_finance_live_ui import open_screen,text

class CurrencyAndCreditTests(unittest.TestCase):
 def test_each_save_slot_uses_its_localized_prefix_without_changing_amounts(self):
  for currency,symbol in ((0,'R$'),(1,'$'),(2,'€')):
   view=l.presentation(l.empty(1043,20260111),20260111,28_000_000,ready=True,nonce='CURRENCY',currency=currency)
   with patch('career_currency.currency_symbol',return_value=symbol):
    vm,screen,_=open_screen(view)
   screen.set('page',1);vm.invoke(screen.get('Refresh'),screen)
   self.assertEqual(text(screen,'summaryValue0'),symbol+' 28.000.000')
   self.assertEqual(text(screen,'summaryValue1'),'+'+symbol+' 1.000.000')
   label=screen.get('amountControl').get('label')
   self.assertEqual(label.get('text').encode('latin1').decode('utf8').strip(),symbol+' 1.000.000')
 def request(self,ident='risk',**extra):
  args=dict(request_id=ident,club=1043,today=20260111,budget=28_000_000,bank=9,amount=5_000_000,months=12,currency=2)
  args.update(extra);return l.request_loan(l.empty(1043,20260111),**args)
 def test_refusal_changes_no_money_and_allows_another_bank_with_its_own_draw(self):
  pending,budget,_=self.request(underwriting_roll=0)
  refused,after,events,decision=l.decide_loan(pending,club=1043,today=20260114,budget=budget)
  self.assertEqual(after,budget);self.assertFalse(decision['approved']);self.assertFalse(refused['contracts']);self.assertNotIn('application',refused)
  self.assertEqual(events[0]['event'],'application_refused')
  notice=mail.make_notice(decision['id'],dict(club=1043,date=20260114,budget=budget),approved=False,bank=9,amount=5_000_000,budget_after=after,message=decision['message'],application=decision,deliver_date=decision['decision_date'])
  self.assertEqual(notice['subject'],'Empréstimo não aprovado');self.assertEqual(notice['due'],20260112)
  second,_,_=l.request_loan(refused,request_id='other-bank',club=1043,today=20260114,budget=after,bank=7,amount=5_000_000,months=12,underwriting_roll=9999)
  approved,after,_,decision=l.decide_loan(second,club=1043,today=20260116,budget=after)
  self.assertTrue(decision['approved']);self.assertEqual(after,budget+5_000_000);self.assertEqual(len(approved['contracts']),1)
 def test_draw_is_frozen_across_reopening_calendar_jumps_and_sql(self):
  pending,budget,_=self.request();before=deepcopy(pending['application'])
  with tempfile.TemporaryDirectory() as folder:
   save=Path(folder)/'DATA';save.write_bytes(b'never change the native save')
   digest=l.fingerprint(save.read_bytes());saved=dict(hash=digest,club=1043,date=20260111,budget=budget)
   sql.save_snapshot(save,saved,pending,[],dict(operation='write',complete_file='1'))
   restored=sql.load_snapshot(save,digest,1043)['state'];self.assertEqual(restored['application'],before)
   for today in (20260112,20260114,20260211):
    _,_,_,decision=l.decide_loan(restored,club=1043,today=today,budget=budget)
    self.assertEqual(decision['approved'],before['underwriting']['roll']>=before['underwriting']['decline_bps'])
   self.assertEqual(save.read_bytes(),b'never change the native save')
 def test_amount_debt_term_and_bank_affect_risk_without_editing_existing_proposals(self):
  state=l.empty(1043,20260111)
  low=l.underwriting(state,'x',28_000_000,9,1_000_000,12,9999)
  high=l.underwriting(state,'x',5_000_000,9,50_000_000,48,9999)
  self.assertGreater(high['decline_bps'],low['decline_bps']);self.assertLessEqual(high['decline_bps'],6500)
  self.assertNotEqual(l.underwriting(state,'x',28_000_000,7,1_000_000,12,1)['decline_bps'],low['decline_bps'])
  pending,budget,_=self.request(underwriting_roll=9999);frozen=deepcopy(pending)
  approved,_,_,decision=l.decide_loan(pending,club=1043,today=20260112,budget=budget)
  self.assertTrue(decision['approved']);self.assertEqual(pending,frozen);self.assertEqual(approved['contracts'][0]['currency'],2)
 def test_old_pending_requests_and_contracts_are_not_rerolled(self):
  pending,budget,_=self.request(underwriting_roll=0);pending['application'].pop('underwriting')
  _,_,_,decision=l.decide_loan(pending,club=1043,today=20260112,budget=budget);self.assertTrue(decision['approved'])
 def test_receipt_decision_and_reminders_keep_the_saved_currency_and_club(self):
  pending,budget,_=self.request(underwriting_roll=9999)
  receipt=mail.request_notice(pending['application']);self.assertIn('{{S16M:2:5000000}}',receipt['body'])
  approved,after,_,decision=l.decide_loan(pending,club=1043,today=20260114,budget=budget)
  contract=approved['contracts'][0]
  notice=mail.make_notice(decision['id'],dict(club=1043,date=20260114,budget=budget,currency=None),
      approved=True,bank=9,amount=5_000_000,budget_after=after,message='Approved',contract=contract)
  self.assertIn('{{S16M:2:5000000}}',notice['body'])
  with tempfile.TemporaryDirectory() as folder:
   mail.schedule_reminders(folder,approved);mail.schedule_reminders(folder,approved)
   rows=json.loads((Path(folder)/'notifications.json').read_text(encoding='utf8'))
   self.assertEqual(len(rows),contract['months']);self.assertTrue(all(r['club']==1043 for r in rows))
   self.assertTrue(all('{{S16M:2:' in r['body'] for r in rows))

if __name__=='__main__':unittest.main()
