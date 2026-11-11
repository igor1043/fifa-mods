import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from . import data,native_titles,worker


def match(i,h,a,hg,ag,*,date=20261101,root=10,asset=1003,stage=11,kind=10,played=True):
    return dict(id=i,home=h,away=a,homeScore=hg,awayScore=ag,date=date,
                root=root,asset=asset,stage=stage,stageKind=kind,played=played)


class NativeTitleTests(unittest.TestCase):
    def test_rollover_startdate_does_not_reset_the_original_title_history(self):
        from title_evidence import career_start
        first=career_start(dict(startdate=20270108),dict(seasoncount=2))
        self.assertEqual(20260101,first)
        titles=native_titles.completed_titles([match(1,1043,2,2,0,date=20261101)],{11:dict(mode='KO1LEG')},{},20270103,first,str)
        self.assertEqual([20261101],[r['date'] for r in titles])
    def titles(self,rows,formats=None,leagues=None):
        return native_titles.completed_titles(rows,formats or {11:dict(mode='KO2LEGS')},leagues or {},20261201,20260101,str)

    def test_two_leg_title_requires_both_legs_and_preserves_competition(self):
        first=match(1,1,2,2,2);second=match(2,2,1,0,2)
        self.assertEqual([],self.titles([first]));self.assertEqual([],self.titles([first,dict(second,played=False)]))
        result=self.titles([first,second]);self.assertEqual([(1003,1)],[(r['competition'],r['club']) for r in result])

    def test_no_title_for_semifinal_future_final_or_unresolved_tie(self):
        for rows in ([match(1,1,2,2,0,kind=8)], [match(1,1,2,2,0,date=20261230)],
                     [match(1,1,2,2,0),match(2,2,1,2,0)]):
            self.assertEqual([],self.titles(rows))

    def test_live_root_alias_keeps_saved_stage_and_uses_unsaved_scores(self):
        saved=match(1,1,2,None,None,played=False)
        snap=dict(nodes=[[10,0,3,1003,0],[11,10,4,-1,10]],fixtures=[[1,10,10,20261101,2000,1,2,3,0,1,1]])
        merged=native_titles.merge_scores([saved],snap,20260101)
        self.assertEqual(11,merged[0]['stage']);self.assertEqual(10,merged[0]['stageKind'])
        result=self.titles(merged,{11:dict(mode='KO1LEG')});self.assertEqual(1,result[0]['club'])
        self.assertIsNone(saved['homeScore'])

    def test_changed_pair_never_inherits_old_final_stage(self):
        saved=match(1,1,2,0,0)
        snap=dict(nodes=[[10,0,3,1003,0]],fixtures=[[1,10,10,20261101,2000,3,4,3,0,1,1]])
        merged=native_titles.merge_scores([saved],snap,20260101)
        self.assertNotEqual(10,merged[0]['stageKind']);self.assertEqual([],self.titles(merged))

    def test_incomplete_league_is_not_a_title_and_full_schedule_is(self):
        rows=[];i=0
        for h in (1,2,3,4):
            for a in range(h+1,5):
                rows.append(match(i,h,a,2,0,root=40,asset=7,stage=41,kind=2));i+=1
        leagues={7:dict(members={1,2,3,4})}
        self.assertEqual([],self.titles(rows[:-1],leagues=leagues))
        self.assertEqual([],self.titles(rows[:-1]+[dict(rows[-1],played=False)],leagues=leagues))
        self.assertEqual(1,self.titles(rows,leagues=leagues)[0]['club'])

    def test_reused_fixture_id_does_not_erase_a_completed_previous_year_final(self):
        saved=match(1,1,2,2,0,date=20261101)
        snap=dict(nodes=[[10,0,3,1003,0],[11,10,4,-1,10]],fixtures=[[1,10,11,20271101,2000,1,2,0,0,0,1]])
        merged=native_titles.merge_scores([saved],snap,20260101)
        self.assertEqual({20261101,20271101},{r['date'] for r in merged})
        titles=native_titles.completed_titles(merged,{11:dict(mode='KO1LEG')},{},20270103,20260101,str)
        self.assertEqual([20261101],[r['date'] for r in titles])

    def test_next_year_schedule_does_not_hide_a_completed_league_or_final(self):
        league=[match(i,h,a,2,0,root=40,asset=7,stage=41,kind=2) for i,(h,a) in enumerate([(1,2),(1,3),(1,4),(2,3),(2,4),(3,4)])]
        future=[dict(m,date=20271101,played=False) for m in league]
        finals=[match(90,1,2,2,0),match(91,2,1,0,1)]
        rows=native_titles.completed_titles(league+future+finals,{11:dict(mode='KO2LEGS')},{7:dict(members={1,2,3,4})},20270103,20260101,str)
        self.assertEqual({7,1003},{r['competition'] for r in rows});self.assertTrue(all(r['year']==2026 for r in rows))

    def test_stalled_market_calls_native_reader_without_advancing_it(self):
        expected=([dict(name='Cup')],'native-proof')
        with (patch.object(data,'market_title_rows',side_effect=ValueError('pending')),
              patch.object(native_titles,'read',return_value=expected) as native):
            self.assertEqual(expected,data.title_rows('game',{'pid':1},'coach'))
        native.assert_called_once_with('game',{'pid':1},'coach')

    def test_national_competition_final_uses_its_original_team_and_cup_ids(self):
        rows=[match(90,1370,1318,2,1,asset=28,stage=11)]
        title=self.titles(rows,{11:dict(mode='KO1LEG')})[0]
        self.assertEqual((28,1370,20261101),(title['competition'],title['club'],title['date']))
    def test_unsaved_national_final_resolves_its_native_group_to_the_final_stage(self):
        snap=dict(nodes=[[10,0,3,28,0],[11,10,4,-1,10],[12,11,5,-1,0]],fixtures=[[1,10,12,20261101,2000,1370,1318,2,1,1,1]])
        merged=native_titles.merge_scores([],snap,20260101)
        self.assertEqual(1370,self.titles(merged,{11:dict(mode='KO1LEG')})[0]['club'])

    def test_failed_native_scope_does_not_accept_stale_market_state(self):
        with (patch.object(data,'market_title_rows',side_effect=ValueError('wrong save')),
              patch.object(native_titles,'read',side_effect=ValueError('wrong scope'))):
            with self.assertRaisesRegex(ValueError,'wrong save'):data.title_rows('game',{'pid':1})

    def test_recovered_market_does_not_hide_previously_earned_native_cups(self):
        old=dict(year=2025,root=1,club=2,name='Earlier club')
        current=dict(year=2026,root=3,club=1043,name='Current cup')
        with (patch.object(data,'market_title_rows',return_value=([old],'market')),
              patch.object(native_titles,'read',return_value=([current],'native'))):
            rows,branch=data.title_rows('game',{'pid':1},'coach')
        self.assertEqual([old,current],rows);self.assertEqual('market:native',branch)


class GalleryServiceTests(unittest.TestCase):
    def test_independent_lane_runs_while_the_calling_room_lane_is_busy(self):
        ready=threading.Event();stop=threading.Event()
        with patch.object(worker,'poll',side_effect=lambda *args:ready.set()):
            thread=threading.Thread(target=worker.watch,args=('game',1,stop),kwargs=dict(alive=lambda:True,interval=.01))
            try:
                thread.start();self.assertTrue(ready.wait(.5))
            finally:stop.set();thread.join(1)
        self.assertFalse(thread.is_alive())

    def test_gallery_poll_does_not_require_a_market_ready_file(self):
        with tempfile.TemporaryDirectory() as temp:
            game=Path(temp);folder=game/'ModCarrerMode/runtime';folder.mkdir(parents=True)
            (folder/'career_fce_snapshot.json').write_text('{}')
            req=dict(pid=1,club=1043,epoch=3,custom=False,page=0,presentation='list')
            with patch.object(worker,'scoped_request',return_value=req),patch.object(worker,'generate',return_value='ok') as generate:
                state={};self.assertTrue(worker.poll(game,1,state));self.assertEqual('ok',state['signature'])
                self.assertTrue(worker.poll(game,1,state));self.assertEqual(1,generate.call_count)


if __name__=='__main__':unittest.main()
