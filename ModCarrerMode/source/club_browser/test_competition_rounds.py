from collections import Counter
import unittest
from competition_rounds import build_rounds

def fixture(id=1,**kw):
 value=dict(id=id,round=7,stage=100,group=0,date=20260711,time='19:00',home=11,away=22,homeScore=2,awayScore=1,played=True)
 value.update(kw);return value

class Matchdays(unittest.TestCase):
 def test_postponed_match_stays_in_native_round_not_calendar_date(self):
  days=build_rounds([fixture(),fixture(2,date=20260802,home=33,away=44),fixture(3,round=8,date=20260718)],20260731)
  self.assertEqual([d['number'] for d in days],[7,8]);self.assertEqual([m['id'] for m in days[0]['matches']],[1,2]);self.assertEqual(days[0]['played'],1)
  self.assertFalse(days[0]['matches'][1]['played'])
 def test_stage_and_group_round_identity_is_preserved(self):
  days=build_rounds([fixture(),fixture(2,stage=101),fixture(3,group=2)],20260731)
  self.assertEqual(len(days),3)
 def test_advanced_round_keeps_its_number_and_numeric_navigation_order(self):
  days=build_rounds([fixture(1,round=37,date=20260711),fixture(2,round=19,date=20260722),fixture(3,round=20,date=20260726)],20260731)
  self.assertEqual([d['number'] for d in days],[19,20,37])
 def test_unplayed_scores_are_not_reported_as_results(self):
  days=build_rounds([fixture(played=False),fixture(2,homeScore=None),fixture(3,date=20260801)],20260731)
  self.assertEqual(days[0]['played'],0)
 def test_duplicate_and_invalid_fixtures_do_not_create_extra_games(self):
  days=build_rounds([fixture(),fixture(),fixture(2,round=0),fixture(3,home=22)],20260731)
  self.assertEqual(len(days),1);self.assertEqual(len(days[0]['matches']),1)
 def test_no_league_id_whitelist_or_invented_rounds(self):
  for stage in (1764,99001,334455):
   days=build_rounds([fixture(stage=stage)],20260731);self.assertEqual(days[0]['stage'],stage)
  self.assertEqual(build_rounds([fixture(round=None)],20260731),[])

if __name__=='__main__':unittest.main(verbosity=2)
