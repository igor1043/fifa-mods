"""Portable regressions for cup phases, return legs and tournament trees."""
import unittest
from competition_cups import build_cup
from competition_bracket import build

class Cups(unittest.TestCase):
 def match(self,i,stage,home,away,h,a):return dict(id=i,stage=stage,stageKind=7,date=20260101+i,home=home,away=away,homeScore=h,awayScore=a,played=True,group=stage+1)
 def test_aggregate_keeps_the_first_home_orientation(self):
  m=[self.match(1,100,11,22,3,0),self.match(2,100,22,11,2,0)]
  result=build_cup({},99,{},m,11,20260130,formats={100:dict(root=99,kind=7,name='Quartas',mode='KO2LEGS')});tie=result['rounds'][0]['ties'][0]
  self.assertEqual((tie['aggregateHome'],tie['aggregateAway'],tie['winner']),(3,2,11));self.assertFalse(result['eliminated'])
 def test_first_leg_does_not_eliminate_opponent(self):
  result=build_cup({},99,{},[self.match(1,100,11,22,3,0)],22,20260130,formats={100:dict(root=99,kind=7,name='Quartas',mode='KO2LEGS')})
  self.assertFalse(result['eliminated']);self.assertIsNone(result['rounds'][0]['ties'][0]['winner'])
 def test_penalty_winner_is_not_invented(self):
  result=build_cup({},99,{},[self.match(1,100,11,22,1,0),self.match(2,100,22,11,1,0)],11,20260130)
  self.assertIsNone(result['rounds'][0]['ties'][0]['winner'])
 def test_same_teams_in_different_phases_stay_separate(self):
  result=build_cup({},99,{},[self.match(1,100,11,22,1,0),self.match(2,200,22,11,2,0)],11,20260130)
  self.assertEqual(len(result['rounds']),2)
 def test_center_final_uses_actual_advancement(self):
  rounds=[dict(stage=100,kind=8,ties=[]),dict(stage=200,kind=10,ties=[])]
  formats={100:dict(groups=[101,102]),200:dict(groups=[201])}
  result=build(rounds,formats,[(101,1,201,1),(102,1,201,2)]);nodes={n['id']:n for n in result['nodes']}
  self.assertEqual(result['final'],201);self.assertEqual((nodes[201]['x'],nodes[201]['y']),(0,0));self.assertLess(nodes[101]['x']*nodes[102]['x'],0);self.assertEqual(len(result['edges']),2)

if __name__=='__main__':unittest.main(verbosity=2)
