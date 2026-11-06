import json,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from test_engine import catalog,context,matches
from engine import Market
from market_balance import dismissal_risk,reputation_delta

class ContinuityTests(unittest.TestCase):
 def test_reload_saved_day_is_exact_even_when_new_tables_or_contract_offers_arrive(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'catalog.db');m=Market(root/'market.db',root/'catalog.db')
   m.open_save('initial','DATA',context())
   with m.db:
    m.advance(context(20261203,matches(60)))
    m.db.execute('UPDATE appointments SET contract_end=20261203 WHERE branch=? AND end_date IS NULL',(m.branch,))
    m.checkpoint('saved','DATA');expected=json.loads(zlib.decompress(m.snapshot()))
   m.close();m=Market(root/'market.db',root/'catalog.db')
   m.open_save('saved','DATA',context(20261203))
   with m.db:m.advance(context(20261203,matches(100)))
   actual=json.loads(zlib.decompress(m.snapshot()));actual['info'].update(id=expected['info']['id'],kind=expected['info']['kind'])
   self.assertEqual(expected,actual);m.close()

 def test_year_rollover_keeps_incumbents_and_past_year_history_after_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'catalog.db');m=Market(root/'market.db',root/'catalog.db');m.open_save('initial','DATA',context())
   with m.db:
    m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key IN ('resignation_bps','poach_bps','enabled')",(m.branch,))
    m.advance(context(20261231,matches(60)))
    m.db.execute('UPDATE appointments SET contract_end=20301231 WHERE branch=? AND end_date IS NULL',(m.branch,))
    m.checkpoint('year-end','DATA')
   def history(market):return sorted([{k:v for k,v in row.items() if k!='branch'} for row in market.rows('results')],key=lambda r:r['match_key'])
   original={a['club_id']:a['coach_id'] for a in m.rows('appointments','end_date IS NULL')};past=history(m);m.close()
   m=Market(root/'market.db',root/'catalog.db');m.open_save('year-end','DATA',context(20261231))
   next_year=dict(context(20270102),season=20270101)
   with m.db:m.advance(next_year);m.checkpoint('new-year','DATA')
   self.assertEqual(original,{a['club_id']:a['coach_id'] for a in m.rows('appointments','end_date IS NULL')});self.assertEqual(past,history(m));self.assertEqual(60,len(m.rows('results')))
   m.close();m=Market(root/'market.db',root/'catalog.db');m.open_save('new-year','DATA',next_year)
   self.assertEqual(original,{a['club_id']:a['coach_id'] for a in m.rows('appointments','end_date IS NULL')});self.assertEqual(past,history(m));m.close()

 def test_balanced_dismissal_and_gradual_reputation_follow_club_expectation(self):
  weak=dict(games=20,losses=12,percentage=25);positive=dict(games=20,losses=6,percentage=55)
  self.assertGreater(dismissal_risk(6000,dict(reputation=8),weak),dismissal_risk(6000,dict(reputation=8),positive))
  self.assertEqual(0,dismissal_risk(6000,dict(reputation=5),positive));self.assertLessEqual(dismissal_risk(6000,dict(reputation=9),positive),25)
  self.assertEqual(0,dismissal_risk(6000,dict(reputation=9),dict(games=9,losses=0,percentage=77.8)))
  self.assertGreater(reputation_delta(positive,40),0);self.assertLess(reputation_delta(positive,70),0)
  self.assertLessEqual(abs(reputation_delta(weak,75)),.06)
  risks=[dismissal_risk(6000,dict(reputation=9),dict(games=20,losses=10,percentage=p)) for p in (55,50,49.9,45,40,39.9,30,20,0)]
  self.assertEqual(sorted(risks),risks);self.assertLess(risks[5]-risks[4],10)

 def test_reputation_review_is_once_per_month_and_survives_checkpoint(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'catalog.db');m=Market(root/'market.db',root/'catalog.db');m.open_save('initial','DATA',context())
   with m.db:
    m.ingest(matches(12),20260220);club=m.one('clubs','club_id',1);a=m.active(club=1)
    m.update_reputation(club,a,20260220,1,20);first=m.one('coaches','coach_id',a['coach_id'])['reputation']
    m.update_reputation(club,a,20260225,1,20);self.assertEqual(first,m.one('coaches','coach_id',a['coach_id'])['reputation']);self.assertEqual(1,len(m.rows('reputation_events')))
    m.checkpoint('saved','DATA')
   m.open_save('saved','DATA',context());self.assertEqual(1,len(m.rows('reputation_events')));self.assertEqual(first,m.one('coaches','coach_id',a['coach_id'])['reputation']);m.close()

if __name__=='__main__':unittest.main()
