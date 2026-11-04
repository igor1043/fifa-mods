import json,unittest
from test_engine import EngineTest,context
class Protection(EngineTest):
 def test_unbeaten_six_wins_three_draws_is_protected(self):
  a=self.m.active(club=1)
  self.m.add('appointment_campaigns',dict(appointment=a['id'],season=20260101,competition_key='db:100',root=0,asset=100,game_date=20260401,baseline=json.dumps([0]*6),counters=json.dumps([3,2,0,3,1,0]),source='test'))
  self.assertTrue(self.m.protected_campaign(a,20260401))
 def test_poor_campaign_not_protected(self):
  a=self.m.active(club=1)
  self.m.add('appointment_campaigns',dict(appointment=a['id'],season=20260101,competition_key='db:100',root=0,asset=100,game_date=20260401,baseline=json.dumps([0]*6),counters=json.dumps([0,0,4,1,0,4]),source='test'))
  self.assertFalse(self.m.protected_campaign(a,20260401))
