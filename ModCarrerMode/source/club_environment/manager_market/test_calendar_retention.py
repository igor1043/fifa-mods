from pathlib import Path
import tempfile, unittest
from unittest.mock import patch
from live_sampler import Sampler

class CalendarRetentionTests(unittest.TestCase):
    def test_calendar_replay_keeps_last_season_titles_after_startdate_rollover(self):
        from live_sampler import calendar_context
        final=dict(id=1,root=10,asset=28,stage=11,stageKind=10,date=20261101,home=1370,away=1318,homeScore=2,awayScore=1,played=True)
        context=dict(clubs=[],fixtures=[],season=20270108,title_start=20260101,title_fixtures=[final],title_formats={11:dict(mode='KO1LEG')},title_labels={28:'Copa'})
        snapshot=dict(date=20270103,nodes=[[10,0,3,28,0],[11,10,4,-1,10]],fixtures=[[1,10,11,20271101,2000,1370,1318,0,0,0,1]],standings=[])
        result=calendar_context(context,snapshot,[])
        self.assertEqual([(28,1370,20261101)],[(r['asset'],r['club'],r['date']) for r in result['titles']])
    def test_national_job_is_retained_even_when_league_rows_do_not_change(self):
        sampler=Sampler(None,None,None,None,None,None,None,None,lambda:0)
        observed=dict(date=20260102,save=dict(pid=1,process_created_100ns=2,path='DATA'),profile=dict(context_address=3,context_epoch=4,club_id=5))
        token=('read','1','DATA')
        for nation in (0,1370):
            sampler.retain(observed,token,dict(date=20260102,rows=[],revision='unchanged',snapshot={'date':20260102},national_job=dict(date=20260102,team=nation,source='live_context')))
        with patch.object(sampler,'capture_journal'):rows=sampler.drain(observed,token,20260101)
        self.assertEqual(1370,rows[0]['snapshot']['national_job']['team'])
    def test_drain_keeps_files_until_sql_commit_then_keeps_current_day(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            old=root/'20260101.campaign.json';old.write_text('confirmed')
            current=root/'20260102.campaign.json';current.write_text('current')
            sampler=Sampler(None,None,root,None,None,None,None,None,lambda:0)
            observed=dict(date=20260102,save=dict(pid=1,process_created_100ns=2,path='DATA'),
                          profile=dict(context_address=3,context_epoch=4,club_id=5))
            token=('read','1','DATA')
            for day,path in ((20260101,old),(20260102,current)):
                stamp=(path.stat().st_mtime_ns,path.stat().st_size)
                sampler.retain(observed,token,dict(date=day,rows=[],snapshot={'date':day}),((path,stamp),))
            with patch.object(sampler,'capture_journal'):
                rows=sampler.drain(observed,token,20260101)
            self.assertEqual([20260101,20260102],[r['date'] for r in rows])
            self.assertTrue(old.exists() and current.exists())
            sampler.discard_committed(20260102)
            self.assertFalse(old.exists())
            self.assertTrue(current.exists())
            sampler.discard_committed(20260102)
            self.assertTrue(current.exists())

    def test_unconfirmed_or_replaced_evidence_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            pending=root/'20260101.campaign.json';pending.write_text('original')
            changed=root/'20260102.campaign.json';changed.write_text('original')
            sampler=Sampler(None,None,root,None,None,None,None,None,lambda:0)
            observed=dict(date=20260103,save=dict(pid=1,process_created_100ns=2,path='DATA'),
                          profile=dict(context_address=3,context_epoch=4,club_id=5))
            token=('read','1','DATA')
            for day,path in ((20260101,pending),(20260102,changed)):
                stamp=(path.stat().st_mtime_ns,path.stat().st_size)
                sampler.retain(observed,token,dict(date=day,rows=[],snapshot={'date':day}),((path,stamp),))
            # No acknowledged SQL publication means no disk deletion.
            sampler.discard_committed(20260103)
            self.assertTrue(pending.exists() and changed.exists())
            with patch.object(sampler,'capture_journal'):
                sampler.drain(observed,token,20260101)
            changed.write_text('new native revision')
            sampler.discard_committed(20260103)
            self.assertFalse(pending.exists())
            self.assertTrue(changed.exists())

    def test_league_only_rows_remain_available_for_calendar_catchup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/'20260101.tsv';path.write_text('league')
            stamp=(path.stat().st_mtime_ns,path.stat().st_size)
            sampler=Sampler(None,None,root,None,None,None,None,None,lambda:0)
            observed=dict(date=20260102,save=dict(pid=1,process_created_100ns=2,path='DATA'),
                          profile=dict(context_address=3,context_epoch=4,club_id=5))
            token=('read','1','DATA')
            sampler.retain(observed,token,dict(date=20260101,rows=[]),((path,stamp),))
            with patch.object(sampler,'capture_journal'):
                sampler.drain(observed,token,20260101)
            sampler.discard_committed(20260102)
            self.assertTrue(path.exists())

if __name__=='__main__':unittest.main()
