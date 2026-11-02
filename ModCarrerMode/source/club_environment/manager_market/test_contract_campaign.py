import unittest
from unittest.mock import patch
import engine as e
from model import project
import test_global_performance as fixtures
native=fixtures.native
from test_engine import context

class ContractCampaignTest(unittest.TestCase):
 setUp=fixtures.GlobalEngineTest.setUp
 tearDown=fixtures.GlobalEngineTest.tearDown
 def profile(self,coach):return next(p for p in project(self.m)['people'] if p['id']==coach)
 def advance(self,c):
  with self.m.db:self.m.advance(c)
 def test_aggregate_profile_and_new_contract_does_not_inherit(self):
  c=context(20260401);c['performance']=[native(1,20260401,10)]
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,));self.advance(c)
  self.assertEqual(10,self.profile('1')['career']['total']['games']);self.assertEqual(0,len(self.m.rows('results')))
  from club_profile import spell
  self.assertEqual(10,spell(self.m.db,self.m.branch,1,20260401)['campaign_stats']['games'])
  old=self.m.active(club=1);self.m.leave(old,20260401,'dismissal','test');self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260401,'hired')
  self.advance(c);self.assertEqual(0,self.profile('4')['career']['total']['games']);self.assertEqual(10,self.profile('1')['career']['total']['games'])
  c['date']=20260410;c['performance']=[native(1,20260410,12)];self.advance(c);self.assertEqual(2,self.profile('4')['career']['total']['games']);self.advance(c);self.assertEqual(2,self.profile('4')['career']['total']['games'])
 def test_short_term_and_renewal_length(self):
  a=self.m.active(club=1);self.m.leave(a,20260201,'dismissal','test')
  with patch.object(e,'draw',return_value=0):self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260201,'hired')
  self.assertEqual(20261231,self.m.active(club=1)['contract_end'])
  a=self.m.active(club=1);self.m.leave(a,20260202,'renewed','test');self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260202,'renewal');self.assertEqual(20270202,self.m.active(club=1)['contract_end'])
 def test_background_partial_poll_preserves_native_contract_baseline(self):
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,))
  c=context(20260401);c['performance']=[native(1,20260401,8)];self.advance(c)
  self.m.leave(self.m.active(club=1),20260401,'dismissal','test');self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260401,'hired');self.advance(c)
  c.update(date=20260410,performance=[native(1,20260410,10)]);self.advance(c)
  self.assertEqual(2,self.profile('4')['career']['total']['games'])
  partial=dict(c,coverage=dict(league_only=True),performance=[dict(native(1,20260410,10),key='db:100',root=0,asset=100,source='live_league')])
  native_rows=self.m.rows('appointment_campaigns');self.advance(partial)
  self.assertEqual(native_rows,self.m.rows('appointment_campaigns'));self.assertEqual(2,self.profile('4')['career']['total']['games'])
  c.update(date=20260420,performance=[native(1,20260420,12)]);self.advance(c)
  self.assertEqual(4,self.profile('4')['career']['total']['games'])
 def test_native_view_goals_survive_reload_without_inheriting_predecessor(self):
  c=context(20260401);c['performance']=[dict(native(1,20260401,5),hw=3,hd=0,hl=0,aw=2,ad=0,al=0,hgf=9,hga=0,agf=4,aga=1)]
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,));self.advance(c)
  p=self.profile('1')['career']['total'];self.assertEqual((5,5,13,1,100.0),(p['games'],p['wins'],p['gf'],p['ga'],p['percentage']))
  self.advance(c);self.assertEqual(13,self.profile('1')['career']['total']['gf'])
  old=self.m.active(club=1);self.m.leave(old,20260401,'dismissal','test');self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260401,'hired');self.advance(c)
  self.assertEqual(0,self.profile('4')['career']['total']['games']);self.assertEqual(0,self.profile('4')['career']['total']['gf'])
 def test_refusal_frees_coach_and_preserves_human(self):
  self.m.db.execute('UPDATE appointments SET contract_end=20260102 WHERE branch=?',(self.m.branch,))
  with patch.object(e,'draw',return_value=0):self.advance(context(20260102))
  self.assertIsNone(self.m.active(coach='1'));self.assertTrue(self.m.rows('movements',"coach_id='1' AND kind='resignation'"));self.assertEqual('USER-42',self.m.active(club=3)['coach_id'])

 def test_same_games_from_scores_and_counters_are_not_added_twice(self):
  c=context(20260103,[dict(id=1,root=1,asset=100,stage=2,date=20260102,home=1,away=2,hg=0,ag=1,played=True,season=20260101)])
  c['performance']=[dict(native(1,20260103,1),hl=1,al=0)]
  self.advance(c);self.assertEqual(1,self.profile('1')['career']['total']['games'])
  branch=self.m.branch;path=self.m.path;catalog=self.m.catalog;self.m.db.commit();self.m.close();self.m=e.Market(path,catalog);self.m.branch=branch
  self.assertEqual(1,self.profile('1')['career']['total']['games'])

 def test_penalty_outcome_replaces_draw_instead_of_adding_another_game(self):
  c=context(20260103,[dict(id=1,root=1,asset=100,stage=2,date=20260102,home=1,away=2,hg=0,ag=0,played=True,season=20260101)])
  c['performance']=[dict(native(1,20260103,1),hw=1,al=0)]
  self.advance(c);s=self.profile('1')['career']['total']
  self.assertEqual((1,1,0,0),(s['games'],s['wins'],s['draws'],s['losses']))

 def test_closed_initial_spell_recovers_handover_counts_only(self):
  c=context(20260401);c['performance']=[dict(native(1,20260401,10),hgf=12,hga=2,agf=8,aga=4)]
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,));self.advance(c)
  old=self.m.active(club=1);self.m.leave(old,20260401,'dismissal','test');self.m.appoint(self.m.one('coaches','coach_id','4'),self.m.one('clubs','club_id',1),20260401,'hired')
  self.m.db.execute('DELETE FROM appointment_campaigns WHERE branch=? AND appointment=?',(self.m.branch,old['id']))
  self.advance(c);self.assertEqual(10,self.profile('1')['career']['total']['games']);self.assertEqual(0,self.profile('4')['career']['total']['games'])
  self.advance(c);self.assertEqual(10,self.profile('1')['career']['total']['games'])
 def test_future_evidence_cannot_be_backdated_into_closed_spell(self):
  c=context(20260401);c['performance']=[native(1,20260401,10)];self.advance(c)
  old=self.m.active(club=1);self.m.leave(old,20260301,'dismissal','test');self.m.db.execute('DELETE FROM appointment_campaigns WHERE branch=? AND appointment=?',(self.m.branch,old['id']))
  from appointment_campaign import retain_closed
  retain_closed(self.m,c);self.assertFalse(self.m.rows('appointment_campaigns',"appointment='"+old['id']+"'"))
 def test_renewal_negotiates_salary_without_rewriting_old_contract(self):
  self.m.db.execute('UPDATE appointments SET contract_end=20260102 WHERE branch=? AND club_id=1',(self.m.branch,));old=self.m.active(club=1)
  with patch.object(e,'draw',return_value=9999):self.advance(context(20260102))
  renewed=self.m.active(club=1);self.assertNotEqual(old['id'],renewed['id']);self.assertGreater(renewed['contract_end'],20260102)
  historic=self.m.one('appointments','id',old['id']);self.assertEqual(old['monthly_wage'],historic['monthly_wage']);self.assertEqual(20260102,historic['contract_end'])
  self.advance(context(20260102));self.assertEqual(renewed['id'],self.m.active(club=1)['id'])

if __name__=='__main__':unittest.main()
