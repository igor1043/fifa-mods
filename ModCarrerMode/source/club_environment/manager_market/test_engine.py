import json,sqlite3,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
import engine as e
from model import project

def catalog(path):
 db=sqlite3.connect(path);db.executescript('''CREATE TABLE coaches(coach_id TEXT,name TEXT,nationality TEXT,birth_date TEXT,reputation REAL,salary INT,style TEXT,image TEXT,eligible INT,fictional INT);CREATE TABLE clubs(club_id INT,name TEXT,league_id INT,league_name TEXT,country TEXT,region TEXT,reputation REAL,budget INT,level INT);CREATE TABLE club_seed(club_id INT,coach_id TEXT,priority INT);CREATE TABLE rules(key TEXT,value REAL);''')
 for i in range(1,25):db.execute('INSERT INTO coaches VALUES(?,?,?,?,?,?,?,?,?,?)',(str(i),'Treinador '+str(i),'Brasil','1980-01-01',8 if i<4 else 5,50000,'Equilibrado','minifaces/NOTFOUND_DEFAULT.png',1,0))
 for i,rep in ((1,9),(2,3),(3,2)):db.execute('INSERT INTO clubs VALUES(?,?,?,?,?,?,?,?,?)',(i,'Clube '+str(i),100,'Liga','Brasil','América do Sul',rep,100000000,1));db.execute('INSERT INTO club_seed VALUES(?,?,?)',(i,str(i),0))
 db.executemany('INSERT INTO rules VALUES(?,?)',e.DEFAULTS.items());db.commit();db.close()
def context(today=20260101,fixtures=None):return dict(date=today,season=20260101,club=3,userid=42,user_name='Jogador',user_wage=1000,clubs=[],fixtures=fixtures or [],titles=[],cup_exits=[],tables={})
def matches(count):
 return [dict(id=i+1,root=100,asset=100,stage=101,date=e.packed(date(2026,1,4)+timedelta(days=i*3)),home=1 if i%2==0 else 2,away=2 if i%2==0 else 1,hg=0 if i%2==0 else 3,ag=3 if i%2==0 else 0,played=True,season=20260101) for i in range(count)]

class EngineTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.sqlite3');self.m=e.Market(self.root/'world.sqlite3',self.root/'catalog.sqlite3');self.m.open_save('initial','DATA',context())
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def run_to(self,c):
  with self.m.db:self.m.advance(c)
 def test_unique_active_appointments_and_human(self):
  active=self.m.rows('appointments','end_date IS NULL');self.assertEqual(3,len(active));self.assertEqual(3,len({a['coach_id'] for a in active}));self.assertEqual('USER-42',self.m.active(club=3)['coach_id'])
 def test_initial_tenure_uses_save_start_but_new_hires_keep_actual_date(self):
  c=context(20260120);c['career_start_date']=20250701;self.run_to(c);self.assertEqual(20250701,self.m.active(club=1)['start_date']);self.m.leave(self.m.active(club=1),20260120,'dismissal','Desempenho');self.m.hire(self.m.one('clubs','club_id',1),20260120,'seed');self.assertEqual(20260120,self.m.active(club=1)['start_date'])
 def test_statistics_home_away_and_no_replay(self):
  c=context(20260120,matches(5));self.run_to(c);self.run_to(c);stats=self.m.stats('1');self.assertEqual(5,stats['total']['games']);self.assertEqual(3,stats['home']['games']);self.assertEqual(2,stats['away']['games']);self.assertEqual(15,stats['total']['ga']);self.assertEqual(5,len(self.m.rows('results')))
 def test_result_arriving_after_morning_date_tick_is_reviewed(self):
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key IN ('min_tenure_days','min_tenure_games')",(self.m.branch,));self.run_to(context(20260104));self.run_to(context(20260104,matches(1)));self.assertTrue(self.m.rows('reviews','club_id=1'));self.assertEqual(1,self.m.stats('1')['total']['games'])
 def test_three_dismissals_max_and_protected_tenure(self):
  self.m.db.execute("UPDATE market_rules SET value=10000 WHERE branch=? AND key IN ('position_weight','form_weight','points_weight','relegation_weight','max_dismissal_bps')",(self.m.branch,));self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key IN ('pressure_threshold','resignation_bps','poach_bps')",(self.m.branch,));self.m.db.execute("UPDATE market_rules SET value=100 WHERE branch=? AND key='max_dismissals_year'",(self.m.branch,))
  with patch.object(e,'draw',return_value=0):self.run_to(context(20261231,matches(120)))
  fired=self.m.rows('movements',"club_id=1 AND kind='dismissal'");self.assertEqual(3,len(fired));dates=sorted(x['game_date'] for x in fired);self.assertTrue(all(e.elapsed(a,b)>=60 for a,b in zip([20260101]+dates,dates)));self.assertFalse(self.m.rows('movements',"club_id=3 AND kind='dismissal'"));self.assertTrue(self.m.rows('salary_events',"kind='salary'"))
 def test_restore_discards_future_events_and_preserves_old_checkpoint(self):
  self.run_to(context(20260120,matches(5)));self.m.checkpoint('saved20','DATA');branch=self.m.branch;self.run_to(context(20260220,matches(15)));self.assertGreater(len(self.m.rows('results')),5);self.m.open_save('saved20','DATA',context(20260120));self.assertNotEqual(branch,self.m.branch);self.assertEqual(5,len(self.m.rows('results')));self.assertEqual(20260120,self.m.info()['game_date'])
 def test_honours_link_actual_coach_and_competition_and_are_idempotent(self):
  c=context(20260110,matches(3));c['titles']=[dict(root=100,asset=100,club=2,date=20260110,season=20260101,name='Liga')];self.run_to(c);self.run_to(c);h=self.m.rows('honours');self.assertEqual(1,len(h));self.assertEqual('2',h[0]['coach_id']);self.assertEqual(100,h[0]['competition_id'])
 def test_disabled_simulation_still_records_results(self):
  self.m.db.execute("UPDATE market_rules SET value=0 WHERE branch=? AND key='enabled'",(self.m.branch,));self.run_to(context(20261001,matches(90)));self.assertFalse(self.m.rows('movements',"kind='dismissal'"));self.assertEqual(90,len(self.m.rows('results')))
 def test_new_club_is_added_without_hardcoded_catalog_row(self):
  c=context(20260102);c['clubs']=[dict(club_id=500,name='Novo clube',league_id=600,league_name='Nova liga',country='Brasil',region='América do Sul',reputation=3,budget=1000000,level=1)];self.run_to(c);self.assertIsNotNone(self.m.active(club=500));self.assertEqual(600,self.m.one('clubs','club_id',500)['league_id'])
 def test_ui_model_age_reputation_and_history(self):
  self.run_to(context(20260120,matches(5)));m=project(self.m);self.assertEqual(3,len(m['clubRows']));self.assertTrue(m['freeRows']);self.assertEqual(sorted([r[6] for r in m['freeRows']],reverse=True),[r[6] for r in m['freeRows']]);self.assertTrue(any(p['details'][2].startswith('5 J') for p in m['people']))
 def test_market_has_new_generation_after_many_future_seasons(self):
  c=context(20850101);c['season']=20850101;self.run_to(c);self.assertTrue(self.m.rows('coaches',"coach_id LIKE 'REGEN-%'"));self.assertTrue(self.m.rows('movements',"kind='retirement'"));self.assertIsNotNone(self.m.active(club=1));self.assertIsNotNone(self.m.active(club=2));self.assertEqual('USER-42',self.m.active(club=3)['coach_id'])
 def test_vacant_club_gets_interim_when_no_candidate_is_eligible(self):
  a=self.m.active(club=1);self.m.leave(a,20260102,'dismissal','Teste');self.m.db.execute('UPDATE coaches SET eligible=0 WHERE branch=?',(self.m.branch,));self.assertTrue(self.m.hire(self.m.one('clubs','club_id',1),20260102,'seed'));self.assertTrue(self.m.active(club=1)['coach_id'].startswith('INTERIM-'));self.assertEqual(self.m.active(club=1)['monthly_wage'],self.m.rows('movements',"kind='interim_appointed'")[0]['new_salary'])
 def test_dismissals_and_hires_are_separate_newest_first(self):
  for club,today in ((1,20260105),(2,20260106)):
   self.m.leave(self.m.active(club=club),today,'dismissal','Desempenho');self.m.hire(self.m.one('clubs','club_id',club),today,'seed')
  data=project(self.m);self.assertEqual(2,len(data['moveRows']));self.assertEqual(2,len(data['hireRows']));self.assertEqual('Clube 2',data['moveRows'][0][0]);self.assertEqual('Clube 2',data['hireRows'][0][0]);self.assertIn('Origem:',data['hireRows'][0][2]);self.assertIn('/ mês',data['hireRows'][0][3])
 def test_atomic_rollback_on_invalid_result(self):
  before=len(self.m.rows('results'));bad=matches(1);bad[0]['hg']=None
  self.run_to(context(20260110,bad));self.assertEqual(before,len(self.m.rows('results')))

if __name__=='__main__':unittest.main()
