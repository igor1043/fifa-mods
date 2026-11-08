import copy,unittest,tempfile
from pathlib import Path
from collections import OrderedDict
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock,patch
from test_engine import EngineTest,context,matches
from model import project
from profile_query import build as query_profile

class ProfileQueryTest(unittest.TestCase):
 setUp=EngineTest.setUp
 tearDown=EngineTest.tearDown
 run_to=EngineTest.run_to
 def test_targeted_cv_matches_full_projection_and_never_scans_whole_tables(self):
  self.run_to(context(20260120,matches(5)))
  complete=project(self.m);light=project(self.m,lightweight=True)
  for person in light['people'][:5]:
   expected=next(p for p in complete['people'] if p['id']==person['id'])
   calls=[];rows=self.m.rows
   def selected(table,where='',args=()):
    calls.append((table,where));return rows(table,where,args)
   with patch.object(self.m,'rows',side_effect=selected),self.m.db.read_batch():actual=query_profile(self.m,person)
   for key in ('career','overview','visualData','spellCards','titleCards','yearCards','contract','confidence'):self.assertEqual(expected[key],actual[key],(person['id'],key))
   self.assertTrue(all(where for table,where in calls));self.assertFalse(actual['profilePending'])
 def test_brazil_league_campaign_not_masked_by_state_wins(self):
  a=self.m.active(club=1);club=self.m.one('clubs','club_id',1)
  import json
  def counters(key,asset,values):self.m.add('appointment_campaigns',dict(appointment=a['id'],season=20260101,competition_key=key,root=asset,asset=asset,game_date=20260401,baseline=json.dumps([0]*6),counters=json.dumps(values),source='test'))
  counters('league',100,[1,1,3,1,1,3]);counters('state',200,[10,0,0,10,0,0])
  self.assertGreater(self.m.appointment_performance(a,20260401)['percentage'],65)
  self.assertGreater(self.m.dismissal_risk(club,a,20260401,70,self.m.policy()),0)
  self.assertEqual(0,self.m.dismissal_risk(dict(club,country='Espanha'),a,20260401,70,self.m.policy()))
 def test_short_or_unbeaten_league_campaign_remains_protected(self):
  import json
  a=self.m.active(club=1);club=self.m.one('clubs','club_id',1)
  self.m.add('appointment_campaigns',dict(appointment=a['id'],season=20260101,competition_key='league',root=100,asset=100,game_date=20260401,baseline=json.dumps([0]*6),counters=json.dumps([3,2,0,3,1,0]),source='test'))
  self.assertEqual(0,self.m.dismissal_risk(club,a,20260401,100,self.m.policy()))

class FastServiceTest(unittest.TestCase):
 def observed(self):return dict(date=20260120,save=dict(pid=10,process_created_100ns=20,path='slot/DATA'),profile=dict(club_id=3,context_address=30,context_epoch=2))
 def service(self):
  from worker import Service,view_scope
  s=Service.__new__(Service);s.market=SimpleNamespace(branch='career',db=SimpleNamespace(read_batch=nullcontext),info=lambda:{'game_date':20260120})
  s.model_cache=({'date':20260120,'profileToken':'scope','people':[{'id':'coach'}],'lazyProfiles':True},'unchanged')
  s.latest_request={'keep':'mounted','observed_scope':view_scope(self.observed())};s.context={};s.history_input=None;s.profile_input=None;s.history_cache=OrderedDict();s.profile_cache=OrderedDict()
  return s
 def test_history_publishes_without_name_error_or_full_screen_render(self):
  s=self.service();old=s.latest_request;request={'identity':(1,'click'),'club':10}
  data={'club':10,'name':'Clube','crest':'crest_10','rows':[['Técnico']]}
  with patch('club_history.request',return_value=request),patch('club_history.build',return_value=data) as query,patch('live_payload.publish') as publish,patch('worker.log'):
   s.service_history(self.observed());s.service_history(self.observed())
  query.assert_called_once();publish.assert_called_once();self.assertEqual(request['identity'],s.history_input);self.assertIs(s.latest_request,old)
 def test_profile_publishes_data_only_and_reuses_scoped_lru(self):
  s=self.service();old=s.latest_request;click={'identity':(1,'click'),'person':0,'coach':'coach'}
  with patch('profile_request.read',return_value=click),patch('profile_query.build',return_value={'id':'coach'}) as query,patch('worker.profile_payload',return_value='encoded-cv'),patch('live_payload.publish') as publish,patch('worker.project',side_effect=AssertionError('Full market projection forbidden')),patch('worker.log'):
   s.service_profile(self.observed());click['identity']=(2,'repeat');s.service_profile(self.observed())
  query.assert_called_once();self.assertEqual(2,publish.call_count);self.assertIs(s.latest_request,old)
  self.assertEqual('profile',publish.call_args.args[3]['kind'])
 def test_same_date_new_save_cannot_query_previous_market(self):
  s=self.service();observed=self.observed();observed['profile']['context_epoch']=3
  with patch('profile_request.read') as profile,patch('club_history.request') as history:
   s.service_profile(observed);s.service_history(observed)
  profile.assert_not_called();history.assert_not_called()

if __name__=='__main__':unittest.main()
