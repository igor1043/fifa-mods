"""Real standings can contain games for which FIFA retains no fixture."""
import copy,unittest
from career_results import summaries,club_stats,from_career
from ranking_core import calculate,reconcile
from test_rankings import team,match,META,RULES
from coach_data import apply_results,attach_market
from unittest.mock import patch

def fixture(i=1,**kw):return dict(match(i,**kw),asset=7)
def snapshot():return dict(date=20260120,nodes=[[1,0,3,7,0],[2,1,4,-1,0],[3,2,5,-1,0]],fixtures=[],standings=[[1,2,1,2,1,0,1,0,0,4],[2,3,1,2,1,0,1,0,0,4]])
def evidence(s=None,fixtures=None):
 r=summaries(s or snapshot(),fixtures or [],{1:7,2:7},[],20260120,20260101,20260120);r['seasonStart']=20260101;return r

class CareerResults(unittest.TestCase):
 def test_parent_and_leaf_not_counted_twice(self):
  r=evidence();s=club_stats(r,1);self.assertEqual((s['games'],s['wins'],s['draws'],s['losses']),(4,3,1,0));self.assertEqual(s['percentage'],83.33);self.assertEqual(s['home']['games']+s['away']['games'],4)
 def test_missing_scores_are_unknown_not_zero_or_fictional_fixtures(self):
  s=club_stats(evidence(),1);self.assertEqual(s['goalsFor'],-1);self.assertEqual(s['goalsAgainst'],-1)
 def test_known_scores_can_supply_all_home_and_away_goals(self):
  r=evidence(dict(snapshot(),standings=[]),[fixture(),fixture(2,home=2,away=1,h=2,a=2)]);s=club_stats(r,1);self.assertEqual((s['games'],s['goalsFor'],s['goalsAgainst']),(2,3,2));self.assertEqual(s['away']['goalsFor'],2)
 def test_duplicate_detailed_fixture_once_and_no_future_or_previous_season(self):
  r=evidence(dict(snapshot(),standings=[]),[fixture(),fixture(),fixture(2,date=20260121),fixture(3,date=20250120)]);self.assertEqual(club_stats(r,1)['games'],1)
 def test_aggregate_difference_only_once_and_points_separate(self):
  games=[fixture()];data=calculate([team(1),team(2)],games,META,20260120,RULES);r=reconcile(data,games,evidence(fixtures=games),META,RULES);row=next(r for r in r['groups']['clubs'] if r['id']==1);self.assertEqual((row['games'],row['wins'],row['draws'],row['losses']),(4,3,1,0));self.assertEqual(row['campaignGames'],3);self.assertEqual(len(row['recent']),1);self.assertGreater(row['campaignPoints'],0)
 def test_full_fixture_coverage_adds_no_campaign_points(self):
  games=[fixture()];e=evidence(dict(snapshot(),standings=[]),games);r=reconcile(calculate([team(1),team(2)],games,META,20260120,RULES),games,e,META,RULES);self.assertEqual(r['aggregateTeamAppearances'],0)
 def test_penalty_campaign_counters_win_over_regulation_draw_without_fake_score(self):
  games=[fixture(h=1,a=1)];s=dict(snapshot(),standings=[[1,2,1,1,0,0,0,0,0,1]])
  e=evidence(s,games);r=reconcile(calculate([team(1),team(2)],games,META,20260120,RULES),games,e,META,RULES);row=next(r for r in r['groups']['clubs'] if r['id']==1)
  self.assertEqual((row['games'],row['wins'],row['draws']),(1,1,0));self.assertEqual(row['campaignPoints'],0);self.assertEqual(row['recent'][0]['score'],'1–1')
 def test_old_detailed_season_does_not_hide_current_aggregate(self):
  games=[fixture(date=20250120)];r=reconcile(calculate([team(1),team(2)],games,META,20260120,RULES),games,evidence(),META,RULES);row=next(r for r in r['groups']['clubs'] if r['id']==1);self.assertEqual(row['games'],5);self.assertEqual(row['campaignGames'],4)
 def test_reload_older_save_has_no_future_totals(self):
  games=[];s=dict(snapshot(),date=20260101,standings=[]);e=summaries(s,games,{1:7,2:7},[],20260101,20260101,20260101);r=reconcile(calculate([team(1),team(2)],games,META,20260101,RULES),games,e,META,RULES);self.assertTrue(all(x['games']==0 for x in r['groups']['clubs']))
 def test_no_stock_league_results_as_save_fallback(self):
  class Cache:
   def table(self,*args):raise AssertionError('Stock data used')
  r=from_career('.',Cache(),[],object(),dict(snapshot(),standings=[]),[]);self.assertEqual(r['summaries'],[])
 def test_coach_team_summary_uses_same_totals_and_does_not_make_up_form(self):
  data=dict(club=1,stats={},competitions=[],fields=dict(form='V'));apply_results(data,evidence(),{7:'Nova liga'});self.assertEqual(data['stats']['games'],4);self.assertEqual(data['competitions'][0]['wins'],3);self.assertEqual(data['fields']['form'],'V')
 def test_aggregate_cannot_be_assigned_to_replacement_coach(self):
  data=dict(club=1,stats=club_stats(evidence(),1),competitions=[],fields=dict(form='V',date=20260120,season_start=20260101))
  market=dict(appointments=['new'],start=20260110,initial=False,results=[],appointment=dict(origin='Contratado',monthly_wage=10),coach=dict(name='Novo',coach_id='USER-0',nationality=''))
  with patch('coach_portrait.portrait',return_value=''):attach_market(data,market,snapshot(),'.')
  self.assertEqual(data['coach_stats'],{});self.assertEqual(data['stats']['games'],4);self.assertIn('coach_stats_note',data['fields'])
 def test_partial_fce_and_league_fallback_do_not_double_count_any_club(self):
  row=dict(teamid=1,leagueid=7,secondarytable=0,homewins=2,homedraws=1,homelosses=0,awaywins=1,awaydraws=0,awaylosses=0,nummatchesplayed=4,points=10,homegf=4,homega=2,awaygf=2,awayga=0)
  e=summaries(snapshot(),[],{1:7,2:7},[row],20260120,20260101,20260120,live=True)
  self.assertEqual(club_stats(e,1)['games'],4)
  row.update(homewins=3,nummatchesplayed=5,points=13)
  e=summaries(snapshot(),[],{1:7,2:7},[row],20260120,20260101,20260120,live=True)
  self.assertEqual(club_stats(e,1)['games'],5)
  self.assertEqual(len([r for r in e['performance'] if r['asset']==7 and r['club']==1]),1)
 def test_initial_coach_owns_whole_campaign_only_with_proof(self):
  data=dict(club=1,stats=club_stats(evidence(),1),competitions=[],fields=dict(form='V',date=20260120,season_start=20260101))
  market=dict(appointments=['initial'],start=20260101,initial=True,results=[],appointment=dict(origin='Vínculo inicial desde o início da carreira',monthly_wage=10),coach=dict(name='Inicial',coach_id='USER-0',nationality=''))
  with patch('coach_portrait.portrait',return_value=''):attach_market(data,market,snapshot(),'.')
  self.assertEqual(data['coach_stats']['games'],4)

if __name__=='__main__':unittest.main()
