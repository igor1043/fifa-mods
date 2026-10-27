"""Dynamic, per-club installment mail and acknowledgements across save/load."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import loans as loan
import loan_notifications as mail
import save_sidecar as sql


class InstallmentMailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.out = self.folder/'transport'
        self.out.mkdir()
        self.state, self.budget, _ = loan.borrow(loan.empty(1043, 20260108),
            request_id='flamengo-loan', club=1043, today=20260108,
            budget=28_000_000, bank=9, amount=3_000_000, months=12)
        self.live = dict(club=1043, date=20260207, budget=self.budget, context_epoch=9)

    def rows(self):
        return json.loads((self.folder/'notifications.json').read_text(encoding='utf8'))

    def send(self, state=None):
        mail.dispatch(self.folder, self.out, self.live, pid=20, context=0x1000,
            state=self.state if state is None else state)

    def payload(self):
        return dict(line.split('=',1) for line in (self.out/'native_mail_request.tsv').read_text(encoding='ascii').splitlines())

    def ack(self, notice, day=20260207):
        (self.out/'native_mail_receipt.tsv').write_text(
            f"pid=20\nclub=1043\ncontext=1000\nepoch=9\nid={notice['id']}\ndate={day}\n", encoding='ascii')

    def test_each_actual_installment_has_its_own_fixed_previous_day_and_amount(self):
        mail.schedule_reminders(self.folder, self.state)
        first = deepcopy(self.rows())
        mail.schedule_reminders(self.folder, self.state)
        self.assertEqual(self.rows(), first)
        self.assertEqual(len(first), 12)
        self.assertEqual(len({n['id'] for n in first}), 12)
        for notice, payment in zip(first, self.state['contracts'][0]['payments']):
            self.assertEqual(notice['club'], 1043)
            self.assertEqual(notice['request_id'], 'flamengo-loan')
            self.assertEqual(notice['payment_date'], payment['date'])
            self.assertEqual(loan.next_day(notice['due']), payment['date'])
            self.assertIn(mail.money(payment['amount']), notice['body'])
            self.assertIn(f"{payment['number']}/12", notice['body'])
        self.live['date'] = 20260206
        self.send()
        self.assertFalse((self.out/'native_mail_request.tsv').exists())
        self.live['date'] = 20260207
        self.send()
        self.assertEqual(self.payload()['id'], first[0]['id'])

    def test_both_dismissal_and_a_foreign_contract_block_the_previous_clubs_mail(self):
        mail.schedule_reminders(self.folder, self.state)
        self.send()
        self.assertTrue((self.out/'native_mail_request.tsv').exists())
        self.live['club'] = 1629
        self.send()
        self.assertFalse((self.out/'native_mail_request.tsv').exists())
        other = loan.empty(1629, 20260108)
        other['contracts'] = deepcopy(self.state['contracts'])
        other_folder = self.folder/'gremio'
        other_folder.mkdir()
        mail.schedule_reminders(other_folder, other)
        self.assertFalse((other_folder/'notifications.json').exists())
        self.live['club'] = 1043
        # A mismatched ledger cannot be used even if a stale row matches live.club.
        self.send(other)
        self.assertFalse((self.out/'native_mail_request.tsv').exists())

    def test_early_payment_suppresses_its_reminder_and_keeps_next_installment(self):
        mail.schedule_reminders(self.folder, self.state)
        self.state, self.budget, events = loan.pay(self.state,
            request_id='early', club=1043, today=20260109, budget=self.budget)
        self.send()
        self.assertFalse((self.out/'native_mail_request.tsv').exists())
        mail.payment_notice(self.folder, self.state,
            dict(club=1043, date=20260109, budget=31_000_000), self.budget, events)
        mail.payment_notice(self.folder, self.state,
            dict(club=1043, date=20260109, budget=31_000_000), self.budget, events)
        notices = self.rows()
        self.assertEqual(sum(n['kind']=='payment' for n in notices), 1)
        confirmation = next(n for n in notices if n['kind']=='payment')
        self.send()
        self.assertEqual(self.payload()['id'], confirmation['id'])
        self.ack(confirmation)
        self.send()
        self.live['date'] = 20260307
        self.send()
        second = next(n for n in notices if n.get('number')==2)
        self.assertEqual(self.payload()['id'], second['id'])

    def test_receipt_consumed_after_due_day_preserves_real_delivery_without_resending(self):
        mail.schedule_reminders(self.folder, self.state)
        reminder = self.rows()[0]
        self.send()
        self.ack(reminder)
        # FIFA inserted the email yesterday; Python first sees its receipt today.
        self.live['date'] = 20260208
        self.state, self.budget, _ = loan.advance(self.state,
            club=1043, today=20260208, budget=self.budget)
        self.send()
        self.assertFalse((self.out/'native_mail_request.tsv').exists())
        delivered = self.rows()[0]
        self.assertTrue(delivered['delivered'])
        self.assertEqual(delivered['delivered_date'], 20260207)
        self.send()
        self.assertEqual(self.rows()[0], delivered)

    def test_missing_a_career_day_does_not_send_a_false_tomorrow_notice(self):
        mail.schedule_reminders(self.folder, self.state)
        for day in (20260208, 20260210, 20260228):
            self.live['date'] = day
            self.send()
            self.assertFalse((self.out/'native_mail_request.tsv').exists())
        self.live['date'] = 20260307
        self.send()
        self.assertEqual(self.payload()['id'], self.rows()[1]['id'])

    def test_a_new_contract_schedules_new_mail_without_replaying_the_paid_contract(self):
        mail.schedule_reminders(self.folder, self.state)
        old_ids = {n['id'] for n in self.rows()}
        self.state, self.budget, _ = loan.pay(self.state,
            request_id='settle', club=1043, today=20260109, budget=self.budget, settle=True)
        self.state, self.budget, _ = loan.borrow(self.state,
            request_id='second-loan', club=1043, today=20260110,
            budget=self.budget, bank=3, amount=1_000_000, months=12)
        mail.schedule_reminders(self.folder, self.state)
        mail.schedule_reminders(self.folder, self.state)
        rows = self.rows()
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({n['id'] for n in rows}), 24)
        new = [n for n in rows if n['id'] not in old_ids]
        self.assertEqual(len(new), 12)
        self.assertEqual(new[0]['due'], 20260209)
        self.live['date'] = 20260207
        self.send()
        self.assertFalse((self.out/'native_mail_request.tsv').exists())
        self.live['date'] = 20260209
        self.send()
        self.assertEqual(self.payload()['id'], new[0]['id'])

    def test_existing_contract_uses_its_saved_bank_name_if_the_catalog_changes(self):
        contract = self.state['contracts'][0]
        original = contract['bank_name']
        with patch.dict(loan.BANKS[9], name='Nome novo para futuras propostas'):
            mail.schedule_reminders(self.folder, self.state)
            self.assertTrue(all(n['body'].splitlines()[0]==original for n in self.rows()))
            state, after, events = loan.pay(self.state, request_id='pay', club=1043,
                today=20260109, budget=self.budget)
            mail.payment_notice(self.folder, state,
                dict(club=1043, date=20260109, budget=self.budget), after, events)
            self.assertEqual(self.rows()[-1]['body'].splitlines()[0], original)

    def test_sqlite_reload_restores_dates_and_ack_without_touching_native_data(self):
        save = self.folder/'DATA'
        save.write_bytes(b'native save unchanged')
        mail.schedule_reminders(self.folder, self.state)
        first = self.rows()[0]
        self.send()
        self.ack(first)
        self.send()
        sql.save_session_club(save, 'hash', 'session', 10, self.state, self.rows())
        restored = sql.load_session_clubs(save, 'hash', 'session',
            dict(operation='read', access_tick_ms=10))[1043]
        self.assertEqual(restored['state'], self.state)
        self.assertEqual(restored['notifications'], self.rows())
        mail.write_json(self.folder/'notifications.json', restored['notifications'])
        mail.schedule_reminders(self.folder, restored['state'])
        self.send(restored['state'])
        self.assertFalse((self.out/'native_mail_request.tsv').exists())
        with sql.connection(save) as db:
            row = db.execute('SELECT due_date,delivered FROM loan_outbox WHERE notice_id=?', (first['id'],)).fetchone()
            self.assertEqual(row, (20260207, 1))
        self.assertEqual(save.read_bytes(), b'native save unchanged')


if __name__ == '__main__':
    unittest.main()
