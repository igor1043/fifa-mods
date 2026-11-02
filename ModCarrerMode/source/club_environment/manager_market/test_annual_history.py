import json
from pathlib import Path
import tempfile
import unittest
from test_engine import catalog,context
from engine import Market
from model import project


def counters(today,n,season=20260101):
 return dict(key='db:100',root=0,asset=100,group=100,club=1,date=today,season=season,source='live_league',hw=n,hd=0,hl=0,aw=0,ad=0,al=0,played=n)


class AnnualHistory(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();r=Path(self.tmp.name);catalog(r/'cat.sqlite3');self.m=Market(r/'world.sqlite3',r/'cat.sqlite3');self.m.open_save('A','DATA',context())
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,))
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def update(self,today,n,season=20260101):
  c=context(today);c['season']=season;c['performance']=[counters(today,n,season)]
  with self.m.db:self.m.advance(c)
 def profile(self):return next(p for p in project(self.m)['people'] if p['id']=='1')
 def test_same_contract_and_prior_year_survive_native_season_change_and_reload(self):
  self.update(20261231,10);a=dict(self.m.active(club=1));self.update(20270110,2,20270101)
  self.assertEqual(a['id'],self.m.active(club=1)['id']);p=self.profile()
  self.assertEqual(12,p['career']['total']['games']);self.assertEqual({2026:10,2027:2},{y['year']:y['total']['games'] for y in p['career']['years']})
  self.m.checkpoint('B','DATA');self.m.open_save('B','DATA',context(20270110));self.assertEqual(a['id'],self.m.active(club=1)['id']);self.assertEqual(12,self.profile()['career']['total']['games'])
 def test_unsaved_new_year_resets_counters_without_erasing_previous_campaign(self):
  self.update(20261231,10);self.update(20270101,0);self.update(20270120,2)
  p=self.profile();self.assertEqual(12,p['career']['total']['games']);self.assertEqual({2026:10,2027:2},{y['year']:y['total']['games'] for y in p['career']['years']})
  previous=[dict(r) for r in self.m.rows('annual_campaigns','year=2026')];self.update(20270120,2);self.assertEqual(previous,self.m.rows('annual_campaigns','year=2026'))
 def test_league_continuing_across_january_records_only_new_year_increment(self):
  self.update(20261231,10);self.update(20270120,12)
  p=self.profile();self.assertEqual(12,p['career']['total']['games']);self.assertEqual({2026:10,2027:2},{y['year']:y['total']['games'] for y in p['career']['years']})
 def test_midyear_season_reset_preserves_both_calendar_year_and_career_totals(self):
  self.update(20261231,10);self.update(20270630,20);self.update(20270701,0,20270701);self.update(20270801,2,20270701)
  p=self.profile();self.assertEqual(22,p['career']['total']['games']);self.assertEqual({2026:10,2027:12},{y['year']:y['total']['games'] for y in p['career']['years']})
 def test_loading_previous_checkpoint_discards_future_year_without_touching_its_history(self):
  self.update(20261231,10);self.m.checkpoint('DEC','DATA');self.update(20270120,2,20270101)
  self.assertEqual(2,len(self.profile()['career']['years']));self.m.open_save('DEC','DATA',context(20261231))
  self.assertEqual([2026],[y['year'] for y in self.profile()['career']['years']]);self.assertEqual(10,self.profile()['career']['total']['games'])
 def test_calendar_year_change_does_not_restore_transferred_coach_to_original_club(self):
  self.update(20261220,8);self.m.db.execute('DELETE FROM annual_campaigns WHERE branch=?',(self.m.branch,));a=self.m.active(club=1);self.m.leave(a,20261221,'resignation','Transferência')
  self.m.leave(self.m.active(club=2),20261221,'dismissal','Teste');self.m.appoint(self.m.one('coaches','coach_id','1'),self.m.one('clubs','club_id',2),20261221,'hired')
  target=self.m.active(club=2)['id'];self.update(20270105,1,20270101);self.assertEqual(target,self.m.active(club=2)['id']);self.assertEqual('1',self.m.active(club=2)['coach_id'])
  self.assertEqual(8,next(y for y in self.profile()['career']['years'] if y['year']==2026)['total']['games'])
 def test_reused_native_fixture_id_in_next_year_is_a_different_match(self):
  def m(day):return dict(id=1,root=100,asset=100,stage=101,date=day,home=1,away=2,hg=2,ag=0,played=True,season=20260101)
  with self.m.db:self.m.advance(context(20261220,[m(20261220)]));self.m.advance(context(20270120,[m(20270120)]))
  self.assertEqual(2,len(self.m.rows('results')));self.assertEqual({2026:1,2027:1},{y['year']:y['total']['games'] for y in self.profile()['career']['years']})

if __name__=='__main__':unittest.main()
