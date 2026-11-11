import json,tempfile,unittest,zlib
from pathlib import Path
from test_engine import catalog,context
from engine import Market
from save_database import NAME,store_receipt

class TitleHistoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.sqlite3')
  self.save=self.root/'A/DATA';self.save.parent.mkdir();self.save.write_bytes(b'native save untouched')
  self.market=Market(self.save.with_name(NAME),self.root/'catalog.sqlite3')
  c=self.ctx(20261203);self.market.open_save('BASE',self.save,c)
  self.market.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.market.branch,))
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def ctx(self,today,titles=()):
  c=context(today);c.update(career_start_date=20260101,titles=list(titles));return c
 def title(self,date,club=3,asset=7,root=10):
  return dict(date=date,club=club,asset=asset,root=root,season=date//10000*10000+101,name='Verified league')
 def update(self,today,titles=()):
  with self.market.db:self.market.advance(self.ctx(today,titles))
 def rows(self):return self.market.rows('trophy_history')
 def test_title_before_market_activation_is_recorded_without_reputation_reward(self):
  self.update(20261204,[self.title(20261120)])
  self.assertEqual(1,len(self.rows()));self.assertEqual('USER-42',self.rows()[0]['coach_id'])
  self.assertEqual([],self.market.rows('honours'));self.assertEqual(20261120,self.rows()[0]['game_date'])
 def test_same_competition_in_new_year_keeps_both_dates_and_is_idempotent(self):
  self.update(20261204,[self.title(20261120)]);self.update(20270103,[self.title(20270102)])
  for _ in range(3):self.update(20270103,[self.title(20270102)])
  self.assertEqual({2026,2027},{r['game_date']//10000 for r in self.rows()});self.assertEqual(2,len(self.rows()))
 def test_unchanged_titles_do_not_dirty_sql_journal_partitions(self):
  from title_history import record
  context=self.ctx(20261204,[self.title(20261120)])
  with self.market.db:
   record(self.market,context);before=self.market.db.total_changes;record(self.market,context)
   self.assertEqual(before,self.market.db.total_changes)
 def test_old_checkpoint_discards_unsaved_new_season_and_another_career_is_isolated(self):
  self.update(20261204,[self.title(20261120)]);self.market.checkpoint('DEC',self.save)
  self.update(20270103,[self.title(20270102)]);self.assertEqual(2,len(self.rows()))
  self.market.open_save('DEC',self.save,self.ctx(20261204));self.assertEqual([20261120],[r['game_date'] for r in self.rows()])
  self.market.open_save('OTHER',self.root/'Other/DATA',self.ctx(20261204));self.assertEqual([],self.rows())
 def test_save_as_carries_the_exact_history_to_its_own_database(self):
  self.update(20261204,[self.title(20261120)]);payload=self.market.snapshot()
  target=self.root/'B/DATA';target.parent.mkdir();target.write_bytes(b'other native save')
  with self.market.db:store_receipt(self.market,target,'SAVEAS',payload,('receipt','SAVEAS',self.market.branch,20261204,7,8,9,'test'))
  other=Market(target.with_name(NAME),self.root/'catalog.sqlite3')
  try:
   other.open_save('SAVEAS',target,self.ctx(20261204));self.assertEqual([20261120],[r['game_date'] for r in other.rows('trophy_history')])
  finally:other.close()
 def test_restored_legacy_day_can_recover_titles_without_resimulating_contracts(self):
  self.update(20261204);self.market.checkpoint('LEGACY',self.save)
  row=self.market.db.execute('SELECT state FROM save_checkpoints WHERE save_hash=?',('LEGACY',)).fetchone()
  payload=json.loads(zlib.decompress(row['state']));payload['tables'].pop('trophy_history');payload['tables'].pop('trophy_national_tenures')
  self.market.db.execute('UPDATE save_checkpoints SET state=? WHERE save_hash=?',(zlib.compress(json.dumps(payload).encode()),'LEGACY'));self.market.db.commit()
  self.market.open_save('LEGACY',self.save,self.ctx(20261204));before=self.market.rows('appointments')
  self.update(20261204,[self.title(20261120)])
  self.assertEqual(1,len(self.rows()));self.assertEqual(before,self.market.rows('appointments'))
 def test_future_and_demonstration_titles_are_never_recorded(self):
  self.update(20261204,[self.title(20270102),dict(self.title(20261120),origin='preview')]);self.assertEqual([],self.rows())
 def national_update(self,today,team,titles=()):
  c=self.ctx(today,titles);c.update(national_teams=[1370,1318],national_jobs=[dict(date=today,team=team,source='live_context')])
  with self.market.db:self.market.advance(c)
 def test_national_titles_follow_the_coach_without_replacing_club_appointment(self):
  before=self.market.active(coach='USER-42')
  self.national_update(20261204,1370)
  self.national_update(20261205,1370,[self.title(20261205,1370,990,99)])
  row=self.rows()[0];self.assertEqual(('USER-42',1370,'national'),(row['coach_id'],row['club_id'],row['team_kind']))
  self.assertEqual(before,self.market.active(coach='USER-42'));self.assertEqual([],self.market.rows('honours'))
 def test_departed_national_team_keeps_old_titles_and_does_not_receive_later_titles(self):
  self.national_update(20261204,1370);self.national_update(20261205,1370,[self.title(20261205,1370,990,99)])
  self.national_update(20261206,1318)
  self.national_update(20261207,1318,[self.title(20261207,1370,990,100),self.title(20261207,1318,991,98)])
  self.assertEqual({('USER-42',1370,20261205),(None,1370,20261207),('USER-42',1318,20261207)},{(r['coach_id'],r['club_id'],r['game_date']) for r in self.rows()})
 def test_national_tenures_rewind_with_the_exact_save(self):
  self.national_update(20261204,1370);self.market.checkpoint('NATION',self.save)
  self.national_update(20270103,1318,[self.title(20270103,1318,990,99)])
  self.market.open_save('NATION',self.save,self.ctx(20261204))
  self.assertEqual([],self.rows());self.assertEqual([1370],[r['team_id'] for r in self.market.rows('trophy_national_tenures')])

if __name__=='__main__':unittest.main()
