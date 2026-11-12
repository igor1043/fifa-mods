import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from engine import Market
from test_engine import catalog,context
from league_title_receipts import completed,definitions
from title_history import record

def table(season=20260109,observed=20270103):
 # Secondary-league W/D/L is native per-club evidence; FIFA does not promise
 # globally paired scores. Do not fabricate fixtures to make it balance.
 return [dict(season=season,key='db:7',club=i+1,date=observed,hw=w,hd=d,hl=l,aw=0,ad=0,al=0)
         for i,(w,d,l) in enumerate(((6,0,0),(3,1,2),(2,1,3),(0,0,6)))]

DEFINITIONS={7:dict(root=10,teams=4,games=6,last_day=339)}

class NativeLeagueTitleTests(unittest.TestCase):
 def test_complete_native_table_recovers_the_past_season_without_an_invented_final(self):
  rows=completed(table(),DEFINITIONS,20271215)
  self.assertEqual(1,len(rows));self.assertEqual((1,20260101,20261231,'completed_native_table:season'),tuple(rows[0][k] for k in ('club','season','date','evidence_source')))
 def test_partial_tied_group_or_early_tables_cannot_create_champions(self):
  self.assertEqual([],completed(table()[:-1],DEFINITIONS,20271215))
  rows=table();rows[1].update(hw=6,hd=0,hl=0)
  self.assertEqual([],completed(rows,DEFINITIONS,20271215))
  self.assertEqual([],completed(table(),{},20271215))
  self.assertEqual([],completed(table(20270101,20270103),DEFINITIONS,20270103))
  self.assertEqual([],completed(table(20270101,20270103),DEFINITIONS,20271215))
  rows=table();rows[0]['key']='fce:10:11:12';self.assertEqual([],completed(rows,DEFINITIONS,20271215))
 def test_installed_definition_uses_all_standing_slots_not_just_seeded_teams(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p=root/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata';p.mkdir(parents=True)
   files={'compobj':'10,3,C7,Liga,0\n11,4,S1,Fase,10\n12,5,G1,Grupo,11\n',
    'settings':'10,asset_id,7\n10,comp_type,LEAGUE\n11,match_stagetype,LEAGUE\n',
    'initteams':'10,0,1\n10,1,2\n','standings':'12,0\n12,1\n12,2\n12,3\n',
    'schedule':''.join(f'11,{i*50},{i},2,2,1600\n' for i in range(1,7))}
   for name,blob in files.items():(p/(name+'.txt')).write_text(blob,encoding='utf8')
   self.assertEqual(4,definitions(root)[7]['teams']);self.assertEqual(6,definitions(root)[7]['games'])

class DurableLeagueTitleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.db')
  self.market=Market(self.root/'world.db',self.root/'catalog.db');c=context(20261203);c['career_start_date']=20260109
  self.market.open_save('BASE','DATA',c)
  self.title=dict(completed(table(),DEFINITIONS,20271215)[0],name='Brasileirão')
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def capture(self,today=20271215):
  c=context(today);c['career_start_date']=20260109
  with patch('league_title_receipts.receipts',return_value=[self.title]):
   with self.market.db:record(self.market,c)
 def test_full_initial_tenure_is_recovered_and_later_replacement_does_not_inherit(self):
  self.market.db.execute('UPDATE appointments SET start_date=20260109 WHERE branch=?',(self.market.branch,))
  self.capture();rows=self.market.rows('trophy_history');self.assertEqual('1',rows[0]['coach_id'])
  before=self.market.one('coaches','coach_id','1');self.capture()
  self.assertEqual(1,len(self.market.rows('trophy_history')));self.assertEqual(before,self.market.one('coaches','coach_id','1'))
  self.assertFalse(self.market.rows('honours'))
 def test_unknown_award_day_does_not_guess_between_two_coaches_in_that_season(self):
  a=self.market.active(club=1);self.market.db.execute('UPDATE appointments SET start_date=20260109 WHERE branch=? AND id=?',(self.market.branch,a['id']))
  self.market.leave(a,20260601,'dismissal','Test');self.market.hire(self.market.one('clubs','club_id',1),20260602,'seed')
  self.capture();self.assertIsNone(self.market.rows('trophy_history')[0]['coach_id'])
 def test_receipt_survives_exact_checkpoint_reload_and_another_season(self):
  self.market.db.execute('UPDATE appointments SET start_date=20260109 WHERE branch=?',(self.market.branch,));self.capture()
  self.market.checkpoint('SAVED','DATA');self.market.open_save('SAVED','DATA',context(20271215))
  self.assertEqual(20260101,self.market.rows('trophy_history')[0]['season'])
  self.title=dict(self.title,season=20270101,date=20271201,evidence_source='completed_native_table:observed',ownership_start=20271201)
  self.capture(20280102);self.assertEqual({2026,2027},{r['season']//10000 for r in self.market.rows('trophy_history')})
 def test_exact_verified_title_keeps_its_actual_date(self):
  row=dict(coach_id='1',club_id=1,season=20260101,competition_id=7,root=10,game_date=20261201,name='Brasileirão',source='confirmed_calendar',team_kind='club')
  self.market.add('trophy_history',row);self.capture();self.assertEqual(20261201,self.market.rows('trophy_history')[0]['game_date'])

if __name__=='__main__':unittest.main()
