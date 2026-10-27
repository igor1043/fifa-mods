import unittest
from datetime import date
from season_stats import totals,age
class SeasonTests(unittest.TestCase):
 def fixture(self,rows):return dict(nodes=[[10,-1,3,5,0],[11,10,4,-1,2],[12,10,4,-1,3]],stats=rows)
 def test_root_total_wins_over_phase_totals(self):
  s=self.fixture([[1,10,1043,9,4,300,2,1],[2,11,1043,9,2,150,1,0],[3,12,1043,9,2,150,1,1]])
  self.assertEqual(totals(s,1043),{9:(4,300,2,1)})
 def test_child_stages_sum_once_and_ignore_other_club(self):
  a=[1,11,1043,9,2,150,1,0];s=self.fixture([a,a,[2,12,1043,9,2,150,1,1],[3,12,1629,9,8,700,5,0]])
  self.assertEqual(totals(s,1043),{9:(4,300,2,1)})
 def test_conflicts_rejected(self):
  with self.assertRaises(ValueError):totals(self.fixture([[1,11,1043,9,2,150,1,0],[2,11,1043,9,3,150,1,0]]),1043)
 def test_missing_is_not_zero(self):self.assertEqual(totals(None,1043),{});self.assertEqual(totals(self.fixture([]),1629),{})
 def test_birthdays_follow_career_date(self):
  birth=(date(1991,12,20)-date(1582,10,14)).days;self.assertEqual(age(birth,20260117),34);self.assertEqual(age(birth,20261220),35);self.assertEqual(age(None,20260117),-1)
