import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_screen
from test_engine import catalog,context
from engine import Market
from global_performance import project
from live_sampler import Sampler,replay
from live_leagues import FIELDS
from datetime import date,timedelta


def league_rows(played):
 return [dict(teamid=i,leagueid=100,secondarytable=0,nummatchesplayed=0,points=0 if i==1 else played*3,homewins=0 if i==1 else played,homedraws=0,homelosses=played if i==1 else 0,awaywins=0,awaydraws=0,awaylosses=0,homegf=0,homega=0,awaygf=0,awayga=0,currenttableposition=i) for i in (1,2)]

def native_campaign(today,played):
 return dict(date=today,nodes=[[1,-1,3,100,0],[2,1,4,101,0]],standings=[[1,2,1,0,0,played,0,0,0,played],[2,2,2,played,0,0,0,0,0,played]],fixtures=[])

class DailyMarket(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'cat.db');self.m=Market(self.root/'world.db',self.root/'cat.db');self.m.open_save('start','DATA',context())
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def evidence(self,date,count):return project(dict(nodes=[],standings=[]),[],{1:100,2:100},league_rows(count),date,20260101,date,'live_league')
 def test_zero_summary_count_uses_confirmed_wdl_and_points(self):
  data=self.evidence(20260301,9)
  self.assertEqual(9,data['tables']['100'][0]['played']);self.assertEqual(27,data['tables']['100'][0]['points']);self.assertEqual(2,len(data['performance']))
 def test_inconsistent_points_are_not_used_to_invent_a_campaign(self):
  rows=league_rows(9);rows[0]['points']=99
  data=project(dict(nodes=[],standings=[]),[],{1:100,2:100},rows,20260301,20260101,20260301,'live_league')
  self.assertNotIn(1,{r['club'] for r in data['performance']})
 def test_first_discovered_campaign_does_not_trigger_mass_dismissals(self):
  c=dict(context(20261201),**self.evidence(20261201,35))
  with patch('engine.draw',return_value=0),self.m.db:self.m.advance(c)
  self.assertFalse(self.m.rows('reviews'));self.assertFalse(self.m.rows('movements',"kind='dismissal'"))
 def test_archived_daily_table_causes_decision_on_its_actual_day(self):
  c=context(20261201);c['clubs']=self.m.rows('clubs')
  with patch('engine.draw',return_value=0),self.m.db:
   replay(self.m,c,[dict(date=d,rows=[],snapshot=native_campaign(d,n)) for d,n in ((20260228,7),(20260301,8),(20260310,9))])
  fired=self.m.rows('movements',"kind='dismissal'")
  self.assertEqual([20260301],[r['game_date'] for r in fired]);self.assertEqual(20260301,self.m.active(club=1)['start_date'])
 def test_stale_timestamped_league_rows_do_not_advance_calendar(self):
  c=context(20261231);c['clubs']=self.m.rows('clubs')
  samples=[dict(date=20260001+m*100,rows=league_rows(0)) for m in range(1,13)]
  with self.m.db:self.assertEqual([],replay(self.m,c,samples))
  self.assertEqual(20260101,self.m.info()['game_date']);self.assertFalse(self.m.rows('reviews'))
 def test_late_season_correction_does_not_trigger_one_day_dismissal_batch(self):
  with patch('engine.draw',return_value=0),self.m.db:
   self.m.advance(dict(context(),**self.evidence(20260101,0)))
   self.m.advance(dict(context(20261201),**self.evidence(20261201,38)))
  self.assertFalse(self.m.rows('reviews'));self.assertFalse(self.m.rows('movements',"kind='dismissal'"))
 def test_old_scores_are_not_relabelled_as_new_decisions(self):
  from test_engine import matches
  with patch('engine.draw',return_value=0),self.m.db:
   self.m.advance(context(20261201));self.m.advance(context(20261207,matches(20)))
  self.assertEqual(20,len(self.m.rows('results')));self.assertFalse(self.m.rows('reviews'))
 def test_january_through_december_backlog_preserves_actual_review_days(self):
  c=context(20261231);c['clubs']=self.m.rows('clubs');samples=[]
  for offset in range(365):
   current=date(2026,1,1)+timedelta(days=offset);d=int(current.strftime('%Y%m%d'));count=offset//7
   samples.append(dict(date=d,rows=[],snapshot=native_campaign(d,count)))
  with patch('engine.draw',return_value=0),self.m.db:processed=replay(self.m,c,samples)
  fired=self.m.rows('movements',"kind='dismissal'");reviews=self.m.rows('reviews')
  self.assertLess(len(processed),100);self.assertEqual(20261231,self.m.info()['game_date'])
  self.assertTrue(fired);self.assertLess(min(r['game_date'] for r in fired),20261101)
  self.assertGreater(len({r['game_date']//100 for r in reviews}),5)
  self.assertTrue(all((date(r['game_date']//10000,r['game_date']//100%100,r['game_date']%100)-date(2026,1,1)).days%7==0 for r in reviews))
 def test_unchanged_days_preserve_renewal_deadline_and_monthly_payroll(self):
  c=context(20260228);c['clubs']=self.m.rows('clubs');self.m.db.execute('UPDATE appointments SET contract_end=20260215 WHERE branch=? AND club_id=1',(self.m.branch,))
  samples=[dict(date=d,rows=[],snapshot=native_campaign(d,0)) for d in (20260201,20260202,20260214,20260215,20260216,20260228)]
  with patch('engine.draw',return_value=9999),self.m.db:processed=replay(self.m,c,samples)
  self.assertIn(20260215,processed);self.assertNotIn(20260202,processed);self.assertTrue(self.m.rows('movements',"club_id=1 AND kind='renewal' AND game_date=20260215"))
  self.assertTrue(self.m.rows('salary_events',"game_date=20260228"))
 def test_journal_restores_intermediate_days_and_rejects_other_load(self):
  o=dict(date=20260401,save=dict(pid=1,process_created_100ns=2,path='DATA'),profile=dict(context_address=3,context_epoch=4,registry_address=6,club_id=5))
  folder=self.root/'league_days/1-2-4-3';folder.mkdir(parents=True)
  for date in (20260301,20260302):
   lines=['schema=1','complete=1','pid=1','process_created_100ns=2','epoch=4','context=3','registry=6','club=5',f'date={date}','captured_ms=100']
   lines+=['league='+','.join(str(r[f]) for f in FIELDS) for r in league_rows(8)]
   (folder/(str(date)+'.tsv')).write_text('\n'.join(lines))
  sampler=Sampler(None,None,self.root,None,None,None,None,None,lambda:50000)
  samples=sampler.drain(o,('read','1','DATA'),20260101)
  self.assertEqual([20260301,20260302],[s['date'] for s in samples])
  other=dict(o,profile=dict(o['profile'],context_epoch=9))
  self.assertEqual([],sampler.drain(other,('read','2','DATA'),20260101))

class DailyCampaign(unittest.TestCase):
 def test_campaign_without_ui_or_league_tsv_is_drained(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'league_days/1-2-3-4';folder.mkdir(parents=True)
   o=dict(date=20260301,save=dict(pid=1,process_created_100ns=2,path='DATA'),profile=dict(context_epoch=3,context_address=4,registry_address=5,club_id=6))
   snap=native_campaign(20260301,8);snap.update(schema=1,complete=1,pid=1,created=2,epoch=3,context=4,registry=5,club=6)
   (folder/'20260301.campaign.json').write_text(json.dumps(snap))
   sampler=Sampler(None,None,root,None,None,None,None,None,lambda:100)
   samples=sampler.drain(o,('read','1','DATA'),20260101)
   self.assertEqual([20260301],[s['date'] for s in samples]);self.assertEqual([],samples[0]['rows']);self.assertEqual(8,samples[0]['snapshot']['standings'][0][9])
 def test_competition_journal_preserves_derived_and_dated_fixtures(self):
  from live_leagues import read_campaign
  from live_sampler import dated_fixtures
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'day.json';o=dict(date=20260301,save=dict(pid=1,process_created_100ns=2),profile=dict(context_epoch=3,context_address=4,registry_address=5,club_id=6))
   data=dict(schema=1,complete=1,pid=1,created=2,epoch=3,context=4,registry=5,club=6,date=20260301,nodes=[[1,-1,3,100,0],[2,1,4,10,0]],standings=[[1,2,10,0,0,0,0,0,0,0]],derivedStandings=[[1,2,10,3,1,0,2,1,0,7,9,1,5,1]],fixtures=[[11,2,10,20260228,1600,10,20,2,0,1,1]])
   path.write_text(json.dumps(data));snap=read_campaign(path,o)
   self.assertEqual(7,snap['standings'][0][9]);self.assertEqual([9,1,5,1],snap['standingGoals']['1'])
   fixtures=dated_fixtures(snap,[],20260101);self.assertEqual(20260228,fixtures[0]['date']);self.assertEqual(2,fixtures[0]['hg'])
   with self.assertRaises(ValueError):read_campaign(path,dict(o,profile=dict(o['profile'],context_epoch=4)))
 def test_retained_day_is_not_requeued_by_heartbeat(self):
  o=dict(date=20260301,save=dict(pid=1,process_created_100ns=2,path='DATA'),profile=dict(context_epoch=3,context_address=4,registry_address=5,club_id=6))
  sampler=Sampler(None,None,None,None,None,None,None,None,None);token=('read','1','DATA');sample=dict(date=20260301,rows=league_rows(8),revision='a')
  sampler.retain(o,token,sample);self.assertEqual(1,len(sampler.drain(o,token,20260101)))
  sampler.retain(o,token,sample);self.assertEqual([],sampler.drain(o,token,20260101))

if __name__=='__main__':unittest.main()
