"""Regression tests for scoped coach identity, results and native request ABI."""
import unittest,tempfile
from pathlib import Path
from coach_data import manager_for,season,tsv,tenure
from lineup_worker import request

class Coach(unittest.TestCase):
 def test_coach_spell_excludes_predecessor_and_ambiguous_hire_day(self):
  f=lambda i,date,home,away,hg,ag:[i,2,0,date,1600,home,away,hg,ag,1]
  snapshot=dict(date=20260110,nodes=[[1,0,3,7,0],[2,1,4,-1,0]],fixtures=[f(1,20260102,1043,1629,0,3),f(2,20260105,1043,1629,0,1),f(3,20260108,1043,1629,2,0),f(4,20260109,1629,1043,1,1),f(5,20260201,1043,1629,8,0)])
  market=dict(appointments=['new'],start=20260105,initial=False,results=[dict(match_key='20260101:1:2:1043:1629',root=1,game_date=20260105,home=1043,away=1629,hg=0,ag=1,home_appointment='old',away_appointment='other')])
  club,_,_=season(snapshot,1043,{7:'Liga'});s,form=tenure(market,snapshot,1043);self.assertEqual(4,club['games']);self.assertEqual((2,1,1,0,3,1),(s['games'],s['wins'],s['draws'],s['losses'],s['goalsFor'],s['goalsAgainst']));self.assertEqual(1,s['home']['games']);self.assertEqual(1,s['away']['games']);self.assertEqual('EV',form)
 def test_returning_coach_does_not_inherit_previous_spell_and_matches_merge_once(self):
  r=lambda ident,when,app:dict(match_key=f'20260101:1:{ident}:1043:1629',root=1,game_date=when,home=1043,away=1629,hg=2,ag=0,home_appointment=app,away_appointment='other')
  snapshot=dict(date=20260120,nodes=[[1,0,3,7,0],[2,1,4,-1,0]],fixtures=[[3,2,0,20260116,1600,1043,1629,2,0,1],[4,2,0,20260119,1600,1629,1043,0,0,1]])
  market=dict(appointments=['new'],start=20260115,initial=False,results=[r(1,20260102,'old'),r(2,20260115,'old'),r(3,20260116,'new')]);s,form=tenure(market,snapshot,1043);self.assertEqual(2,s['games']);self.assertEqual(4,s['points']);self.assertEqual('EV',form)
  market['initial']=True;market['start']=20260101;market['appointments']=['old','new'];s,_=tenure(market,snapshot,1043);self.assertEqual(4,s['games'])
 def test_missing_market_is_unknown_and_tsv_keeps_two_independent_scopes(self):
  self.assertEqual(({},''),tenure(None,None,1043));data=dict(club=1043,club_name='Clube',fields={'name':'Técnico'},stats={'games':12},coach_stats={'games':2},competitions=[],history=[],starters=[]);text=tsv(data).decode();self.assertIn('S\ttotal\t12',text);self.assertIn('T\ttotal\t2',text)
 def test_manager_stats_cannot_leak_between_clubs_or_users(self):
  managers=[dict(teamid=1043,firstname='Real',surname='Coach'),dict(teamid=1629,firstname='Other',surname='Coach')]
  users=[dict(userid=0,usertype=1,clubteamid=1043,firstname='Human')]
  info=[dict(userid=0,clubteamid=1043,wage=38000,boardconfidence=90),dict(userid=9,clubteamid=1629,wage=123)]
  self.assertEqual(manager_for(1043,managers,users,info)['wage'],38000)
  self.assertNotIn('wage',manager_for(1629,managers,users,info))
  self.assertNotIn('wage',manager_for(1043,managers,users,[dict(userid=9,clubteamid=1043,wage=123)]))
  self.assertNotIn('wage',manager_for(1043,managers,[dict(userid=0,usertype=0,clubteamid=1043)],info))
 def test_fixture_rollups_exclude_future_unplayed_and_other_clubs(self):
  f=lambda i,date,home,away,hs,gs,played:[i,2,0,date,1600,home,away,hs,gs,played]
  fixtures=[f(1,20260101,1043,1629,2,0,1),f(2,20260102,1629,1043,1,1,1),f(3,20260120,1043,1629,0,0,0),f(4,20260201,1043,1629,4,0,1),f(5,20260103,3,4,1,2,1)]
  snapshot=dict(date=20260110,nodes=[[1,0,3,7,0],[2,1,4,-1,0]],fixtures=fixtures+[fixtures[0]])
  s,competitions,form=season(snapshot,1043,{7:'Liga'})
  self.assertEqual((s['games'],s['wins'],s['draws'],s['points'],s['goalsFor']),(2,1,1,4,3))
  self.assertEqual(s['home']['games']+s['away']['games'],s['games']);self.assertEqual(form,'EV')
  self.assertEqual(competitions[0]['status'],'Em andamento')
  snapshot['fixtures'][0]=f(1,20260101,1043,1629,3,0,1)
  with self.assertRaises(ValueError):season(snapshot,1043,{7:'Liga'})
 def test_missing_results_are_unknown_not_zero(self):
  self.assertEqual(season(None,1043,{}),({},[],''))
  s,c,f=season(dict(date=20260101,nodes=[],fixtures=[]),1043,{})
  self.assertEqual(s['games'],0);self.assertEqual(c,[])
 def test_coach_request_is_bounded_and_still_reads_other_modes(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'request.tsv'
   def write(kind):path.write_text('schema=1\npid=42\nseq=13\nclub=1043\nkind='+kind+'\n')
   write('coach');self.assertEqual(request(path,42)['kind'],'coach')
   with self.assertRaises(ValueError):request(path,43)
   write('fake-coach')
   with self.assertRaises(ValueError):request(path,42)

if __name__=='__main__':unittest.main()
