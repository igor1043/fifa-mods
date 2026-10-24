"""The actual click must leave the native screen synchronously, without scans."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import runtime as r
import loans as l
from test_finance_live_ui import open_screen


class DirectInputTests(unittest.TestCase):
    def test_native_screen_emits_exactly_one_direct_event_on_explicit_confirmation(self):
        view=l.presentation(l.empty(1043,20260111),20260111,28_000_000,ready=True,nonce='CLICK')
        vm,screen,calls=open_screen(view)
        self.assertFalse(any(c[0]=='SendSystemEvent' and c[1][1]=='Server16SubmitBank' for c in calls))
        screen.set('page',2);screen.set('focus',0);vm.invoke(screen.get('Select'),screen)
        events=[c for c in calls if c[0]=='SendSystemEvent' and c[1][1]=='Server16SubmitBank']
        self.assertEqual(len(events),1)
        self.assertEqual(events[0][1],['Calendar','Server16SubmitBank',vm.global_.get('Server16BankRequestV2')])
        self.assertIn('|20260111|END_S16BANK',events[0][1][2])

    def test_direct_mailbox_is_immediate_and_uses_native_click_date_and_selected_club(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'native_request.tsv'
            payload='schema=1\npid=1\nclub=1043\ncontext=1234\nepoch=7\ndate=20260111\nwire=S16BANK_V3|CLICK|1|0|10|6|1|20260101|END_S16BANK\n'
            p.write_text(payload,encoding='ascii')
            params=dict(pid=1,club=1043,context=0x1234,epoch=7,nonce='CLICK')
            self.assertEqual(r.read_direct_request(folder,**params),[(1,0,10,6,1,20260111)])
            for key,value in (('pid',2),('club',517),('context',0x1235),('epoch',8),('nonce','OLD_SAVE')):
                self.assertFalse(r.read_direct_request(folder,**dict(params,**{key:value})))
            p.write_text(payload.replace('20260111','20261311'))
            self.assertFalse(r.read_direct_request(folder,**params))

    def test_bridge_uses_direct_input_without_reading_the_process_heap(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(r,'STATE',Path(folder)):
            root=Path(folder);b=r.Bridge.__new__(r.Bridge)
            b.process=type('P',(),{'pid':123})();b.club=1043;b.context_address=0x1234;b.nonce='DIRECT'
            b.live=lambda:dict(context_epoch=2)
            b.scan_bounded=lambda:self.fail('A direct click must not scan gigabytes')
            b.request_reader=None
            (root/'native_input_ready.tsv').write_text('schema=1\npid=123\nready=1\n')
            (root/'native_request.tsv').write_text('schema=1\npid=123\nclub=1043\ncontext=1234\nepoch=2\ndate=20260111\nwire=S16BANK_V4|DIRECT|2|1|10|0|1|20260101|loan-two|END_S16BANK\n')
            self.assertEqual(b.scan(),[(2,1,10,0,1,20260111,'loan-two')])
            (root/'native_input_ready.tsv').write_text('schema=1\npid=999\nready=1\n')
            self.assertFalse(b.direct_input_ready())


if __name__=='__main__':unittest.main()
