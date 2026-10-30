from pathlib import Path
import copy,json,unittest
from ranking_core import calculate,importance,expectation,confirmed_titles
from ranking_data import merge_schedule,snapshot_key

RULES=json.loads((Path(__file__).resolve().parents[2]/'data/club_browser/ranking_rules.json').read_text())
def team(i,kind='clubs',overall=75):return dict(id=i,name='Equipe '+str(i),kind=kind,nation=i,confederation=4,countryName='Brasil',leagueName='Liga',overall=overall,international=10)
def match(i=1,home=1,away=2,h=1,a=0,date=20260110,**extra):return dict(id=i,root=1,date=date,home=home,away=away,homeScore=h,awayScore=a,played=True,stage=10,stageKind=2,**extra)
META={1:dict(type='LEAGUE',scope='domestic',strength=75)}

class Rankings(unittest.TestCase):
 def build(self,games,teams=None,today=20260110,titles=(),meta=None):return calculate(teams or [team(1),team(2)],games,meta or META,today,RULES,titles)
 def test_equal_win_moves_winner_and_loser_and_total_is_conserved(self):
  rows=self.build([match()])['groups']['clubs'];self.assertEqual(rows[0]['id'],1);self.assertGreater(rows[0]['matchPoints'],0);self.assertEqual(rows[0]['matchPoints'],-rows[1]['matchPoints']);self.assertEqual(rows[0]['form'],['V'])
 def test_underdog_wins_more_than_favourite(self):
  self.assertGreater(32*(1-expectation(1300,1500)),32*(1-expectation(1500,1300)))
 def test_fifa_published_sum_example(self):self.assertAlmostEqual(1300+25*(1-expectation(1300,1500)),1317.0746496736797,places=7)
 def test_national_final_loser_is_protected(self):
  games=[dict(match(),stageKind=10)];result=self.build(games,[team(1,'nations'),team(2,'nations')],meta={1:dict(type='INTERCUP',scope='world')})['groups']['nations'];self.assertEqual(result[0]['matchPoints'],30);self.assertEqual(result[1]['matchPoints'],0)
 def test_qualifier_loser_does_lose_points(self):
  result=self.build([dict(match(),stageKind=3)],[team(1,'nations'),team(2,'nations')],meta={1:dict(type='INTERQUAL',scope='world')})['groups']['nations'];self.assertLess(result[1]['matchPoints'],0)
 def test_confirmed_title_adds_once_and_rebuild_is_idempotent(self):
  award=dict(team=1,root=1,year=2026,date=20260110);a=self.build([match()],titles=[award]);self.assertGreater(a['groups']['clubs'][0]['titlePoints'],0);self.assertEqual(a,self.build([match()],titles=[award]))
 def test_duplicate_fixture_does_not_duplicate_points(self):self.assertEqual(self.build([match()]),self.build([match(),match()]))
 def test_conflicting_fixture_rejected(self):
  with self.assertRaises(ValueError):self.build([match(),match(h=2)])
 def test_future_incomplete_and_cross_kind_not_counted(self):
  games=[match(date=20260111),dict(match(2),played=False),match(3,away=3)];result=self.build(games,[team(1),team(2),team(3,'nations')]);self.assertEqual(result['matches'],0)
 def test_reload_older_date_does_not_keep_future_points(self):
  a=self.build([match()],today=20260109);self.assertEqual(a['matches'],0);self.assertTrue(all(r['matchPoints']==0 for r in a['groups']['clubs']))
 def test_all_teams_beyond_top_150_present(self):self.assertEqual(len(self.build([],teams=[team(i) for i in range(1,1801)])['groups']['clubs']),1800)
 def test_rules_derive_competition_strength_without_league_allowlist(self):
  a=importance(dict(type='LEAGUE',scope='domestic',strength=85),False,False,RULES);b=importance(dict(type='LEAGUE',scope='domestic',strength=55),False,False,RULES);self.assertGreater(a,b)
 def test_no_title_for_first_leg_or_tied_penalty_final(self):
  teams={i:team(i) for i in (1,2)};formats={10:dict(mode='KO2LEGS')}
  self.assertEqual(confirmed_titles([dict(match(),stageKind=10)],teams,META,20260110,formats),[])
  self.assertEqual(confirmed_titles([dict(match(h=1,a=1),stageKind=10)],teams,META,20260110,{}),[])
 def test_two_legs_aggregate_confirms_correct_winner(self):
  games=[dict(match(h=2,a=0),stageKind=10),dict(match(2,home=2,away=1,h=1,a=0),stageKind=10)]
  titles=confirmed_titles(games,{i:team(i) for i in (1,2)},META,20260110,{10:dict(mode='KO2LEGS')});self.assertEqual(titles[0]['team'],1)
 def test_cross_year_league_does_not_award_first_half(self):
  games=[match(1,1,2,3,0,date=20251201),match(2,1,3,3,0,date=20251202),match(3,2,3,1,0,date=20251203),dict(match(4,2,1,date=20260501),played=False)]
  self.assertEqual(confirmed_titles(games,{i:team(i) for i in (1,2,3)},META,20260110,{}),[])
 def test_entire_league_awards_only_unique_points_leader(self):
  games=[match(1,1,2,3,0),match(2,1,3,3,0),match(3,2,3,1,0)]
  titles=confirmed_titles(games,{i:team(i) for i in (1,2,3)},META,20260110,{});self.assertEqual(titles[0]['team'],1)
 def test_native_new_score_overrides_saved_score_same_identity(self):
  s=dict(nodes=[[1,0,3,7,0],[10,1,4,-1,2]],fixtures=[[1,10,10,20260110,1200,1,2,2,1,1]])
  result=merge_schedule([match(h=0,a=0)],s,{});self.assertEqual(len(result),1);self.assertEqual(result[0]['homeScore'],2)
 def test_generation_counter_is_not_new_result(self):
  a=dict(club=1,date=20260110,fixtures=[],nodes=[],standings=[],generation=1);b=dict(a,generation=2);self.assertEqual(snapshot_key(a),snapshot_key(b));b['date']+=1;self.assertNotEqual(snapshot_key(a),snapshot_key(b))

if __name__=='__main__':unittest.main(verbosity=2)
