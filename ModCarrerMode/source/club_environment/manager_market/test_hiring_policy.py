import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_engine import catalog,context
import engine as e

class HiringPolicyTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);catalog(root/'catalog.sqlite3')
  self.m=e.Market(root/'world.sqlite3',root/'catalog.sqlite3');self.m.open_save('A','DATA',context())
  self.m.db.execute("UPDATE coaches SET eligible=CASE WHEN coach_id IN ('4','5') THEN 1 ELSE 0 END WHERE branch=?",(self.m.branch,))
  self.m.db.execute("UPDATE coaches SET reputation=9,salary=50000 WHERE branch=? AND coach_id IN ('4','5')",(self.m.branch,))
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='quality_exception_bps'",(self.m.branch,))
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def choose(self):
  self.m.leave(self.m.active(club=1),20260120,'dismissal','Teste')
  with patch.object(e,'draw',return_value=5000):self.m.hire(self.m.one('clubs','club_id',1),20260120,'seed')
  return self.m.active(club=1)['coach_id']
 def test_predecessor_nationality_accepts_translations_and_dual_nationality(self):
  self.m.db.execute("UPDATE coaches SET nationality=CASE WHEN coach_id='4' THEN 'Brazil;Italy' ELSE 'Italy' END WHERE branch=? AND coach_id IN ('4','5')",(self.m.branch,))
  self.assertEqual('4',self.choose());self.assertEqual(e.nationalities('Brazil'),e.nationalities('Brasil RS'))
 def test_foreign_predecessor_gets_a_small_preference_over_host_country(self):
  self.m.db.execute("UPDATE coaches SET nationality='Italy' WHERE branch=? AND coach_id IN ('1','4')",(self.m.branch,))
  self.assertEqual('4',self.choose())
 def test_elite_club_keeps_quality_when_a_suitable_free_coach_exists(self):
  self.m.db.execute("UPDATE coaches SET reputation=5 WHERE branch=? AND coach_id='4'",(self.m.branch,))
  self.assertEqual('5',self.choose())
 def test_elite_club_uses_interim_instead_of_permanent_large_downgrade(self):
  self.m.db.execute("UPDATE coaches SET reputation=3 WHERE branch=? AND coach_id IN ('4','5')",(self.m.branch,))
  self.assertTrue(self.choose().startswith('INTERIM-'))
 def test_actual_recent_results_distinguish_equally_qualified_free_coaches(self):
  for i in range(10):
   self.m.add('results',dict(match_key=str(i),season=20260101,root=100,competition_id=100,stage=1,game_date=20260101+i,home=1,away=2,hg=3,ag=0,home_coach='4',away_coach='5',home_appointment=None,away_appointment=None))
  self.assertEqual('4',self.choose())
 def test_version_two_defaults_upgrade_without_overwriting_custom_chance(self):
  for key,value in (('market_policy_version',2),('pressure_threshold',32),('max_dismissal_bps',2100),('dismissal_slope_bps',90)):
   self.m.db.execute('UPDATE market_rules SET value=? WHERE branch=? AND key=?',(value,self.m.branch,key))
  self.m.upgrade_policy();policy=self.m.policy()
  self.assertEqual(30,policy['pressure_threshold']);self.assertEqual(2100,policy['max_dismissal_bps']);self.assertEqual(100,policy['dismissal_slope_bps']);self.assertEqual(3,policy['market_policy_version'])
  self.assertEqual((60,8,7,3),tuple(policy[k] for k in ('min_tenure_days','min_tenure_games','review_gap_days','max_dismissals_year')))

if __name__=='__main__':unittest.main()
