import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_global_performance import GlobalEngineTest,native
from test_engine import context
from model import project
from club_profile import spell


class OwnershipRevision(unittest.TestCase):
 setUp=GlobalEngineTest.setUp
 tearDown=GlobalEngineTest.tearDown
 def advance(self,c):
  with self.m.db:self.m.advance(c)
 def test_midyear_hire_uses_owned_games_even_with_a_legacy_zero_baseline(self):
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,))
  def game(i,date):return dict(id=i,root=1,asset=100,stage=2,date=date,home=1,away=2,hg=1,ag=0,played=True,season=20260101)
  games=[game(1,20260112),game(2,20260120),game(3,20260612),game(4,20260620)]
  self.advance(context(20260120,games))
  self.m.leave(self.m.active(club=1),20260401,'dismissal','test')
  self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260401,'hired')
  c=context(20261201,games);c['performance']=[dict(native(1,20261201,4),hw=4,hd=0,hl=0,aw=0,ad=0,al=0)]
  self.advance(c)
  self.m.db.execute("UPDATE appointment_campaigns SET baseline='[0,0,0,0,0,0]' WHERE branch=? AND appointment=?",(self.m.branch,self.m.active(club=1)['id']))
  self.m.db.execute("UPDATE annual_campaigns SET baseline='[0,0,0,0,0,0]' WHERE branch=? AND appointment=?",(self.m.branch,self.m.active(club=1)['id']))
  p=next(p for p in project(self.m)['people'] if p['id']=='4')
  self.assertEqual(2,p['career']['total']['games']);self.assertEqual(1,len(p['spellCards']));self.assertEqual(1,len(p['yearCards']))
  self.assertEqual(2,p['career']['years'][0]['total']['games']);self.assertEqual(2,spell(self.m.db,self.m.branch,1,20261201)['campaign_stats']['games'])
 def test_old_observation_cannot_give_predecessor_games_to_a_new_hire(self):
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,))
  c=context(20260120);c['performance']=[native(1,20260120,4)];self.advance(c)
  self.m.leave(self.m.active(club=1),20260401,'dismissal','test');self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260401,'hired')
  c=context(20261201);c['performance']=[native(1,20261201,20)];self.advance(c)
  p=next(p for p in project(self.m)['people'] if p['id']=='4');self.assertEqual(0,p['career']['total']['games'])
 def test_coach_profile_imports_in_the_real_package_without_manager_path(self):
  root=Path(__file__).resolve().parent.parent
  env=dict(os.environ,PYTHONPATH=str(root))
  with tempfile.TemporaryDirectory() as tmp:
   script="from manager_market.career_profile import build; p=build({'coach_id':'1'},[],[],[],{},{},20260101,str); assert p['total']['games']==0"
   r=subprocess.run([sys.executable,'-c',script],cwd=tmp,env=env,capture_output=True,text=True)
  self.assertEqual(0,r.returncode,r.stderr)
 def test_hiring_rejects_a_previously_dismissed_coach_when_the_rarity_gate_fails(self):
  from unittest.mock import patch
  import engine
  self.m.leave(self.m.active(club=1),20260301,'dismissal','test')
  self.m.db.execute("UPDATE coaches SET eligible=CASE WHEN coach_id='1' THEN 1 ELSE 0 END WHERE branch=?",(self.m.branch,))
  with patch.object(engine,'draw',return_value=5000):self.m.hire(self.m.one('clubs','club_id',1),20260601,'seed')
  self.assertNotEqual('1',self.m.active(club=1)['coach_id'])

if __name__=='__main__':unittest.main()
