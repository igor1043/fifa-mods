import unittest
from competition_campaign import knockout_first


class Phase(unittest.TestCase):
 def test_groups_stay_first_until_knockout_after_groups(self):
  groups=[dict(stageKind=2,date=20260110,played=True,home=1,away=2),dict(stageKind=2,date=20260120,played=False,home=1,away=3)]
  qualifier=dict(stageKind=100,date=20260101,played=True,home=1,away=4)
  final=dict(stageKind=10,date=20260201,played=False,home=1,away=2)
  self.assertFalse(knockout_first(groups+[qualifier,final],20260115))
  groups[1]['played']=True
  self.assertTrue(knockout_first(groups+[qualifier,final],20260125))
  self.assertFalse(knockout_first(groups+[qualifier],20260125))
 def test_already_played_knockout_stays_first_for_any_competition(self):
  games=[dict(stageKind=2,date=20260101,played=True,home=1,away=2),dict(stageKind=5,date=20260201,played=True,home=1,away=4)]
  self.assertTrue(knockout_first(games,20260202));self.assertFalse(knockout_first(games[:1],20260202))

if __name__=='__main__':unittest.main()
