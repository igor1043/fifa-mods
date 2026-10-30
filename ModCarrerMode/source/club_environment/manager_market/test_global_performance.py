from pathlib import Path
from unittest.mock import patch
import tempfile,unittest
import engine as e
from global_performance import project
from test_engine import catalog,context

def native(club,date,count,key='fce:1:2',asset=100):
 return dict(key=key,root=1,group=2,asset=asset,club=club,date=date,season=20260101,source='fce',hw=0,hd=0,hl=count//2,aw=0,ad=0,al=count-count//2,played=count)

class GlobalProjectionTest(unittest.TestCase):
 def test_empty_setup_does_not_hide_active_groups_and_groups_stay_separate(self):
  nodes=[[1,-1,3,100,0],[2,1,4,-1,1],[3,2,5,-1,0],[4,1,4,-1,0],[5,4,5,-1,0],[6,4,5,-1,0],[10,-1,3,200,0],[11,10,5,-1,0]]
  standings=[[i,3,i,0,0,0,0,0,0,0] for i in range(1,9)]
  standings += [[i+10,5 if i<=4 else 6,i,2,1,1,1,1,2,8] for i in range(1,9)];standings += [[30,11,1,1,0,0,0,0,1,2]]
  p=project(dict(nodes=nodes,standings=standings),[],{i:100 for i in range(1,9)},[],20260101,20260101,20260401)
  self.assertEqual(4,len(p['club_tables']['1']));self.assertEqual({1,2,3,4},{r['club'] for r in p['club_tables']['1']});self.assertEqual({5,6,7,8},{r['club'] for r in p['club_tables']['5']});self.assertEqual(2,p['coverage']['live_competitions']);self.assertEqual(17,len(p['performance']))
 def test_saved_league_summaries_keep_the_saved_date_when_live_league_is_empty(self):
  nodes=[[1,-1,3,100,0],[2,1,5,-1,0]];standings=[[i,2,i,0,0,0,0,0,0,0] for i in (1,2)]
  links=[dict(teamid=i,leagueid=100,secondarytable=0,nummatchesplayed=10,homewins=2,homedraws=1,homelosses=2,awaywins=1,awaydraws=1,awaylosses=3,points=11) for i in (1,2)]
  p=project(dict(nodes=nodes,standings=standings),[],{1:100,2:100},links,20260301,20260101,20260401)
  self.assertEqual(20260301,p['table_dates']['100']);self.assertEqual(2,len(p['tables']['100']));self.assertEqual(0,p['coverage']['live_league_tables']);self.assertTrue(any(r['source']=='saved_league' for r in p['performance']))

class GlobalEngineTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);catalog(root/'cat.sqlite3');self.m=e.Market(root/'world.sqlite3',root/'cat.sqlite3');self.m.open_save('A','DATA',context())
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def observed(self,today,count):
  c=context(today);c['performance']=[native(i,today,count) for i in (1,2,3)];c['tables']={'100':[dict(club=i,played=count,points=count*3 if i==2 else 0,rank=1 if i==2 else 2 if i==3 else 3,gf=0,ga=0) for i in (2,3,1)]};c['table_dates']={'100':today};return c
 def run_to(self,c):
  with self.m.db:self.m.advance(c)
 def test_global_results_trigger_real_replacement_without_fake_fixtures(self):
  with patch.object(e,'draw',return_value=0):self.run_to(self.observed(20260401,10))
  self.assertEqual(1,len(self.m.rows('movements',"club_id=1 AND kind='dismissal'")));self.assertEqual(1,len(self.m.rows('movements',"club_id=1 AND kind='hired'")));self.assertEqual([],self.m.rows('results'));self.assertTrue(self.m.rows('reviews','club_id=1'));self.assertFalse(self.m.rows('reviews','club_id=3'));self.assertFalse(self.m.rows('movements',"club_id=3 AND kind IN ('dismissal','hired','retirement','resignation','poached')"));self.assertEqual('USER-42',self.m.active(club=3)['coach_id'])
 def test_unchanged_aggregate_never_rerolls_and_new_coach_gets_working_period(self):
  with patch.object(e,'draw',return_value=0):
   self.run_to(self.observed(20260401,10));hired=self.m.active(club=1)['coach_id'];self.run_to(self.observed(20260701,10));self.assertEqual(hired,self.m.active(club=1)['coach_id']);self.run_to(self.observed(20260708,12));self.assertEqual(hired,self.m.active(club=1)['coach_id']);self.run_to(self.observed(20260715,18));self.assertNotEqual(hired,self.m.active(club=1)['coach_id'])
  self.assertEqual(2,len(self.m.rows('movements',"club_id=1 AND kind='dismissal'")))
 def test_stale_saved_table_does_not_provoke_current_date_dismissal(self):
  c=self.observed(20260401,10);c['table_dates']['100']=20260101
  with patch.object(e,'draw',return_value=0):self.run_to(c)
  self.assertFalse(self.m.rows('reviews'));self.assertFalse(self.m.rows('movements',"kind='dismissal'"))
 def test_global_path_keeps_three_dismissals_per_year_even_with_high_custom_limit(self):
  self.m.db.execute("UPDATE market_rules SET value=99 WHERE branch=? AND key='max_dismissals_year'",(self.m.branch,))
  with patch.object(e,'draw',return_value=0):
   for today,count in ((20260401,10),(20260603,20),(20260805,30),(20261007,40)):self.run_to(self.observed(today,count))
  self.assertEqual(3,len(self.m.rows('movements',"club_id=1 AND kind='dismissal'")));self.assertEqual('USER-42',self.m.active(club=3)['coach_id'])
 def test_user_club_is_protected_at_hire_and_automatic_exit_boundaries(self):
  a=self.m.active(club=3)
  for kind in ('dismissal','resignation','poached','retirement','renewed'):self.assertFalse(self.m.leave(a,20260401,kind,'Teste'))
  self.assertFalse(self.m.hire(self.m.one('clubs','club_id',3),20260401,'seed'));self.assertEqual(a['id'],self.m.active(club=3)['id'])
 def test_old_defaults_upgrade_once_and_custom_weights_are_preserved(self):
  self.m.db.execute("DELETE FROM market_rules WHERE branch=? AND key IN ('market_policy_version','dismissal_slope_bps')",(self.m.branch,));self.m.db.execute("UPDATE market_rules SET value=36 WHERE branch=? AND key='pressure_threshold'",(self.m.branch,));self.m.db.execute("UPDATE market_rules SET value=2100 WHERE branch=? AND key='max_dismissal_bps'",(self.m.branch,));self.m.upgrade_policy();p=self.m.policy();self.assertEqual(30,p['pressure_threshold']);self.assertEqual(2100,p['max_dismissal_bps']);self.assertEqual(100,p['dismissal_slope_bps']);self.assertEqual(3,p['market_policy_version'])

if __name__=='__main__':unittest.main()
