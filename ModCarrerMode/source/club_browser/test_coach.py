"""Regression tests for scoped coach identity, results and native request ABI."""
import unittest,tempfile
from pathlib import Path
from coach_data import manager_for,season,tsv
from lineup_worker import request

class Coach(unittest.TestCase):
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
