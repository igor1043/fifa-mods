import unittest
from competition_insights import build
from competition_team import build_competition_statistics

def match(id=1,**kw):
 m=dict(id=id,date=20260110,home=11,away=22,homeName='Casa',awayName='Fora',homeScore=3,awayScore=0,played=True);m.update(kw);return m

class Insights(unittest.TestCase):
 def test_cup_short_eliminated_campaign_does_not_win_defense_or_keeper(self):
  long=[match(i,date=20260101+i,stage=10 if i<8 else 20 if i<11 else 30,stageKind=2 if i<8 else 7,homeScore=1,awayScore=1) for i in range(1,13)]
  short=[match(100+i,date=20260101+i,stage=10,stageKind=2,home=33,away=44,homeScore=0,awayScore=0) for i in range(5)]
  keepers=[dict(id=90,club=33,appearances=5,averageRating=9),dict(id=91,club=11,appearances=12,averageRating=7.7)]
  r=build(long+short,20260201,dict(goalkeeper=keepers[0],goalkeepers=keepers),{},cup=True)
  self.assertIn(r['defense']['club'],(11,22));self.assertEqual(9,r['defense']['minimumGames']);self.assertEqual(91,r['goalkeeper']['id']);self.assertEqual(7.7,r['goalkeeper']['averageRating'])
 def test_cup_deeper_round_has_priority_after_minimum_sample(self):
  fixtures=[match(i,date=20260101+i,stage=10,stageKind=5,homeScore=1,awayScore=0) for i in range(1,11)]
  fixtures += [match(100+i,date=20260112+i,stage=30,stageKind=10,home=33,away=44,homeScore=2,awayScore=1) for i in range(8)]
  self.assertIn(build(fixtures,20260201,{}, {},cup=True)['defense']['club'],(33,44))
 def test_played_results_only_no_duplicates_or_other_competition(self):
  m=match();result=build([m,m,match(2,date=20260201,homeScore=9),match(3,played=False,homeScore=8)],20260131,{}, {11:'Casa',22:'Fora'})
  self.assertEqual(result['attack']['gf'],3);self.assertEqual(result['attack']['games'],1);self.assertEqual(result['biggestWin']['id'],1)
 def test_defense_uses_average_and_a_minimum_number_of_games(self):
  fixtures=[match(i,home=11,away=22,homeScore=1,awayScore=0) for i in range(1,7)]+[match(7,home=33,away=44,homeScore=0,awayScore=0)]
  result=build(fixtures,20260131,{},{});self.assertEqual(result['defense']['club'],11);self.assertEqual(result['defense']['minimumGames'],3)
 def test_draws_have_no_biggest_win_and_missing_data_is_not_invented(self):
  result=build([match(homeScore=0,awayScore=0)],20260131,{},{});self.assertNotIn('biggestWin',result);self.assertNotIn('goalkeeper',result);self.assertNotIn('scorer',result)
 def test_biggest_win_preserves_home_away_orientation(self):
  result=build([match(),match(2,homeScore=0,awayScore=5)],20260131,{},{});self.assertEqual((result['biggestWin']['homeScore'],result['biggestWin']['awayScore']),(0,5))
 def test_goalkeeper_uses_valid_ratings_and_root_totals_without_duplicate_stages(self):
  players={90:dict(preferredposition1=0,name='GK A'),91:dict(preferredposition1=0,name='GK B'),92:dict(preferredposition1=0,name='GK C')}
  s=dict(nodes=[[100,0,3],[101,100,4],[200,0,3]],stats=[[1,100,11,90,6,540,0,0,480,2],[2,101,11,90,6,540,0,0,480,2],[3,100,22,91,1,90,0,0,100,2],[4,200,22,91,8,720,0,0,800,2],[5,100,33,92,6,540,0,0,600,0]])
  r=build_competition_statistics(s,[100],players,lambda p:p['name'],{})[100]
  self.assertEqual(r['goalkeeper']['id'],90);self.assertEqual(r['goalkeeper']['appearances'],6);self.assertEqual(r['goalkeeper']['averageRating'],8);self.assertFalse(r['teamOfCompetition']['available'],'Keeper selection must not depend on having a complete XI')

if __name__=='__main__':unittest.main(verbosity=2)
