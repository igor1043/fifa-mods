"""Loan collection and persistence must survive a native-screen build failure."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from apt_actions import Actions
from formats import AptFile, BigFile
from loans import advance, borrow, empty, presentation
import bank_ui_r60 as ui
import runtime as bridge
import save_sidecar as sql
from test_finance_live_ui import open_screen, text


class LoanScreenRecoveryTests(unittest.TestCase):
    def test_large_localized_approved_loan_can_open_and_each_method_is_bounded(self):
        state, budget, _ = borrow(empty(1043, 20260217), request_id='large-loan',
            club=1043, today=20260217, budget=28_625_050, bank=12,
            amount=30_000_000, months=12)
        view = presentation(state, 20260511, 64_399_270, ready=True,
            nonce='RECOVERY', currency=0, wage_budget=190_000)
        vm, screen, calls = open_screen(view)
        self.assertIn('1 de 2', text(screen, 'overviewState'))
        self.assertIn('17/03/2026', text(screen, 'overviewLine1'))
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
        actions = Actions(AptFile(BigFile(ui.b.HERE /
            'package/data/ui/game/screens/career/server16/bankloans.big'))).read_all()
        self.assertFalse(actions.errors)
        for method in ('Refresh', 'RefreshBase', 'RefreshDesign'):
            self.assertIsNotNone(screen.get(method))
        self.assertTrue(all(len(body) < 100_000 for _, body in actions.functions))

    def test_two_long_contracts_retain_localized_individual_statements(self):
        state = empty(1629, 20260102)
        budget = 80_000_000
        for index, bank in enumerate((10, 12)):
            state, budget, _ = borrow(state, request_id='long-'+str(index),
                club=1629, today=20260102, budget=budget, bank=bank,
                amount=50_000_000, months=48)
        view = presentation(state, 20260511, budget, ready=True,
            nonce='TWO_CONTRACTS', currency=2, wage_budget=100_000)
        vm, screen, _ = open_screen(view)
        self.assertIn('2 de 2', text(screen, 'overviewState'))
        self.assertEqual(len(screen.get('loanContracts')), 2)
        self.assertFalse(view['can_borrow'])
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

    def test_ui_failure_does_not_stop_skipped_due_dates_or_native_save_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            save = root/'DATA'
            save.write_bytes(b'isolated native save')
            digest = hashlib.sha256(save.read_bytes()).hexdigest()
            b = bridge.Bridge.__new__(bridge.Bridge)
            b.state, live_budget, _ = borrow(empty(1043, 20260217),
                request_id='kept-contract', club=1043, today=20260217,
                budget=28_625_050, bank=12, amount=30_000_000, months=12)
            original = json.loads(json.dumps(b.state))
            live = dict(club=1043, date=20260511, budget=live_budget,
                page='game/screens/fluxhub/fluxhub')
            b.apply = True
            b.process = SimpleNamespace(pid=123)
            b.club = 1043
            b.context_address = 0
            b.live_wage_valid = False
            b.saved_wage_budget = 190_000
            b.currency = 0
            b.nonce = 'RECOVERY'
            b.result = None
            b.feedback = ''
            b.view_signature = b.ui_signature = None
            b.scope = 'test-scope'
            b.session = 'test-session'
            b.save = dict(path=str(save))
            b.saved_hash = digest
            b.io_tick = 10
            b.club_states = {}
            b.last_scan = 0
            b.last_advance = (None, None)
            b.live = lambda: dict(live)
            b.scan = lambda: []
            b.observe_save = b.refresh_catalog = lambda: None
            b.flush_notifications = lambda _: None
            writes = []

            def publish(before, state, budget, events, reason, result=None):
                writes.extend(event for event in events if event['event']=='installment')
                b.state = state
                live['budget'] = budget

            b.publish = publish
            import bank_ui_r57
            with patch.object(bridge, 'STATE', root), patch.object(bridge, 'log'), \
                    patch('club_identity.club_name', return_value='Clube'), \
                    patch.object(bank_ui_r57, 'build', side_effect=RuntimeError('APT failed')):
                b.tick()
                b.tick()
                self.assertEqual(b.state['contracts'][0]['paid'], 2)
                self.assertEqual([p['number'] for p in writes], [1, 2])
                expected = sum(p['amount'] for p in original['contracts'][0]['payments'][:2])
                self.assertEqual(live['budget'], live_budget-expected)
                recovered = sql.load_session_clubs(save, digest, b.session, {})[1043]['state']
                self.assertEqual(recovered, b.state)
                self.assertEqual(recovered['contracts'][0]['id'], 'kept-contract')
                saved = dict(hash=digest, club=1043, date=live['date'], budget=live['budget'])
                sql.save_snapshot(save, saved, recovered, [],
                    dict(operation='write', complete_file='1', access_tick_ms=11))
                restored = sql.load_snapshot(save, digest, 1043)['state']
                again, after, events = advance(restored, club=1043,
                    today=live['date'], budget=live['budget'])
                self.assertFalse(events)
                self.assertEqual(after, live['budget'])
                self.assertEqual(again, restored)
                self.assertEqual(save.read_bytes(), b'isolated native save')

    def test_screen_retry_keeps_last_good_package_until_validation_succeeds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            relative = 'data/ui/game/screens/career/server16/bankloans'
            target = root/(relative+'v2.big')
            target.parent.mkdir(parents=True)
            target.write_bytes(b'last-good-screen')
            source = root/'package'/(relative+'.big')
            source.parent.mkdir(parents=True)
            source.write_bytes(b'validated-screen')
            b = bridge.Bridge.__new__(bridge.Bridge)
            b.ui_signature = 'old'
            import bank_ui_r57
            with patch.object(bridge, 'HERE', root), patch.object(bridge, 'GAME', root), \
                    patch.object(bridge, 'log'), \
                    patch.object(bridge.time, 'monotonic', side_effect=[10, 11, 14]), \
                    patch.object(bank_ui_r57, 'build', side_effect=[RuntimeError('APT failed'), None]) as build:
                self.assertFalse(b.publish_screen({}, 'new'))
                self.assertEqual(target.read_bytes(), b'last-good-screen')
                self.assertEqual(b.ui_signature, 'old')
                self.assertFalse(b.publish_screen({}, 'new'))
                self.assertTrue(b.publish_screen({}, 'new'))
                self.assertEqual(build.call_count, 2)
                self.assertEqual(target.read_bytes(), b'validated-screen')
                self.assertEqual(b.ui_signature, 'new')
                self.assertIsNone(b.ui_error)


if __name__ == '__main__':
    unittest.main()
