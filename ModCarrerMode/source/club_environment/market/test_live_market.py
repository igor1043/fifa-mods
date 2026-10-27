from pathlib import Path
import copy,json,tempfile,unittest
from live_market import read_live
from read_market import read_snapshot
from market_test_fixture import career_fixture
import worker_market as worker

class LiveMarketTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'live.tsv'
        self.snapshot=dict(save=dict(pid=44),profile=dict(club_id=1043,context_address=0xabc,registry_address=0x123,context_epoch=2),date=20260111)
        self.raw='schema=1\npid=44\nepoch=2\ncontext=abc\nregistry=123\nclub=1043\ndate=20260111\ncaptured_ms=100000\nentry=3\noffer=1,32,2000000,1,1043,0,234,0,20260110,1,1,0,0,0\nplayer=234,0,0,0,82,86,25\nlink=234,1043\ncomplete=1\n'
        self.path.write_text(self.raw,encoding='ascii')
    def tearDown(self):self.folder.cleanup()
    def test_live_rows_and_entry_identity_are_validated(self):
        data=read_live(self.path,self.snapshot,100500)
        self.assertEqual(data['entry'],3);self.assertEqual(data['offers'][0]['result'],32)
        self.assertEqual(data['players'][0]['overallrating'],82);self.assertEqual(data['links'][0]['teamid'],1043)
    def test_other_process_club_date_epoch_and_incomplete_capture_are_rejected(self):
        for a,b in (('pid=44','pid=45'),('club=1043','club=1'),('date=20260111','date=20260110'),('epoch=2','epoch=3'),('context=abc','context=abd'),('complete=1','complete=0')):
            self.path.write_text(self.raw.replace(a,b),encoding='ascii')
            with self.assertRaises(ValueError):read_live(self.path,self.snapshot,100500)
    def test_expired_and_future_capture_are_rejected(self):
        for now in (99999,112001):
            with self.assertRaises(ValueError):read_live(self.path,self.snapshot,now)
    def test_unchanged_capture_time_does_not_rebuild_market(self):
        a=read_live(self.path,self.snapshot,101000)
        self.path.write_text(self.raw.replace('captured_ms=100000','captured_ms=101000'),encoding='ascii')
        b=read_live(self.path,self.snapshot,101500);self.assertEqual(a['revision'],b['revision'])
    def test_unsaved_confirmed_offer_is_counted_without_editing_the_save(self):
        import hashlib
        fixture=career_fixture();game,save=fixture.__enter__();self.addCleanup(fixture.__exit__,None,None,None)
        before=hashlib.sha256(save.read_bytes()).hexdigest();live=read_live(self.path,self.snapshot,100500)
        data=read_snapshot(game,save,club_override=1043,date_override=20260111,live=live)
        self.assertEqual(data['summary']['completedDeals'],1);self.assertEqual(data['summary']['investment'],2000000)
        self.assertEqual(data['transfers'][0]['to']['id'],1043);self.assertEqual(data['source'],'live-career')
        self.assertEqual(hashlib.sha256(save.read_bytes()).hexdigest(),before)
        for changes in ({'links':[]},{'offers':[dict(live['offers'][0],result=16)]},{'offers':[dict(live['offers'][0],date=20260201)]}):
            alternative=dict(live,**changes);data=read_snapshot(game,save,club_override=1043,date_override=20260111,live=alternative)
            self.assertEqual(data['summary']['completedDeals'],0)

if __name__=='__main__':unittest.main(verbosity=2)
