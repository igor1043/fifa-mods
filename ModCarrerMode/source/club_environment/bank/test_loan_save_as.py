"""A native Save As must not erase debt while its new DATA is being replaced."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import runtime as r
import save_sidecar as sql
from loans import empty, borrow, advance


class SaveAsLoanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = self.root/'old/DATA'
        self.new = self.root/'new/DATA'
        for path in (self.old, self.new):
            path.parent.mkdir()
            path.write_bytes(b'native slot '+path.parent.name.encode())
        state, budget, _ = borrow(empty(1043, 20260217), request_id='kept',
            club=1043, today=20260217, budget=28_625_050, bank=12,
            amount=30_000_000, months=12)
        state, budget, _ = advance(state, club=1043, today=20260511, budget=budget)
        self.b = b = r.Bridge.__new__(r.Bridge)
        b.save = dict(path=str(self.old), size=self.old.stat().st_size, mtime_ns=1)
        b.state = state
        b.club = 1043
        b.scope = 'old-scope'
        b.memory = None
        b.io_tick = 10
        b.saved_hash = 'old-hash'
        b.club_states = {1043: dict(state=state, notifications=[])}
        b.snapshots = self.root/'runtime/old-scope/snapshots'
        b.snapshots.mkdir(parents=True)
        self.current = dict(path=str(self.new), size=self.new.stat().st_size, mtime_ns=2)
        self.live = dict(club=1043, date=20260511, budget=budget)
        self.saved = dict(hash=hashlib.sha256(self.new.read_bytes()).hexdigest(),
            club=1043, date=20260511, budget=budget)
        self.record = dict(operation='write', complete_file='1', access_tick_ms='12')
        b.io_record = lambda: self.record
        b.saved = lambda: self.saved
        b.live = lambda: self.live

    def test_transient_read_of_replaced_slot_waits_then_completed_write_keeps_both_payments(self):
        b = self.b
        old_state = json.loads(json.dumps(b.state))
        valid_saved = dict(self.saved)
        self.record = dict(self.record, operation='read')
        self.saved = dict(self.saved, date=20260210, budget=28_625_050)
        with patch.object(r, 'STATE', self.root/'runtime'), patch.object(r, 'log'), \
                patch.object(r, 'read_active_save', return_value=self.current):
            self.assertIs(b.observe_save(), False)
            self.assertEqual(b.save['path'], str(self.old))
            self.assertEqual(b.state, old_state)
            self.assertEqual(b.io_tick, 10)
            self.old.unlink()
            self.record = dict(self.record, operation='write')
            self.saved = valid_saved
            b.observe_save()
        restored = sql.load_snapshot(self.new, self.saved['hash'], 1043)['state']
        self.assertEqual(restored, old_state)
        self.assertEqual(restored['contracts'][0]['paid'], 2)
        self.assertEqual(b.save['path'], str(self.new))

    def test_missing_active_file_during_save_as_suspends_tick_without_discarding_ledger(self):
        b = self.b
        original = json.loads(json.dumps(b.state))
        with patch.object(r, 'STATE', self.root/'runtime'), \
                patch.object(r, 'read_active_save', side_effect=ValueError('replacement not complete')):
            b.refresh_catalog = lambda: self.fail('Financial work must wait for Save As')
            b.tick()
        self.assertEqual(b.state, original)
        self.assertEqual(b.save['path'], str(self.old))

    def test_actual_loaded_slot_still_rebinds_instead_of_inheriting_previous_debt(self):
        self.record = dict(self.record, operation='read')
        with patch.object(r, 'read_active_save', return_value=self.current):
            with self.assertRaisesRegex(RuntimeError, 'Outro slot'):
                self.b.observe_save()
        self.assertEqual(self.b.save['path'], str(self.old))

    def test_same_slot_partial_write_does_not_consume_the_io_event_or_reset_debt(self):
        self.current['path'] = str(self.old)
        self.saved['budget'] -= 1
        with patch.object(r, 'read_active_save', return_value=self.current):
            self.assertIs(self.b.observe_save(), False)
        self.assertEqual(self.b.io_tick, 10)
        self.assertEqual(self.b.state['contracts'][0]['paid'], 2)


if __name__ == '__main__':
    unittest.main()
