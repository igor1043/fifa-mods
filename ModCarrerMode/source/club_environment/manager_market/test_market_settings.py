import json,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
import test_screen
from test_engine import catalog,context,matches
from engine import Market,packed
from market_settings import read,write,request
from native_review_vm import open_native
from screen import FULL,script_factory,stars
from manager_layout import scenes_for
from model import project
from PIL import Image
import native_screen

class SettingsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'cat.db');self.market=Market(self.root/'db',self.root/'cat.db');self.market.open_save('initial','DATA',context())
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def advance(self,today,fixtures=None):
  with self.market.db:self.market.advance(context(today,fixtures))
 def test_defaults_and_user_preferences_survive_reopen_independent_of_save(self):
  file=self.root/'settings.json';self.assertEqual(dict(enabled=True,cadence=1),read(file));write(file,dict(enabled=False,cadence=30));self.advance(20260104,matches(1));self.market.checkpoint('saved','DATA');self.market.open_save('saved','DATA',context(20260104));self.assertEqual(dict(enabled=False,cadence=30),read(file))
  self.assertEqual(1,len(self.market.rows('results')))
  for bad in ({'enabled':'false','cadence':7},{'enabled':True,'cadence':0},{'enabled':True,'cadence':7.0}):
   with self.assertRaises(ValueError):write(file,bad)
 def decisions(self,cadence,last):
  self.market.simulation_settings=dict(enabled=True,cadence=cadence);observed=[]
  def future(today,c,p):
   if p['enabled']:observed.append(today)
  with patch.object(self.market,'future_market',side_effect=future):
   from engine import day
   start=max(date(2026,1,2),day(self.market.info()['game_date'])+timedelta(days=1))
   for index in range((last-start).days+1):self.advance(packed(start+timedelta(days=index)))
  return observed
 def test_daily_is_legacy_and_weekly_runs_once_per_calendar_week(self):
  self.assertEqual([20260102,20260103,20260104],self.decisions(1,date(2026,1,4)))
  self.assertEqual([20260105,20260112,20260119,20260126],self.decisions(7,date(2026,1,31)))
 def test_monthly_crosses_year_and_is_restored_without_duplicate_decisions(self):
  self.assertEqual([20260201,20260301],self.decisions(30,date(2026,3,3)))
  with self.market.db:self.market.checkpoint('march','DATA')
  self.market.open_save('march','DATA',context(20260303));self.advance(20260304)
  row=self.market.rows('market_cycles')[0];self.assertEqual(20260301,row['last_review'])
 def test_disabled_preserves_results_and_never_replays_disabled_decisions(self):
  self.market.simulation_settings=dict(enabled=False,cadence=7)
  with patch.object(self.market,'hire',wraps=self.market.hire) as hired:self.advance(20260201,matches(10));self.assertEqual(0,hired.call_count)
  self.assertEqual(10,len(self.market.rows('results')));self.assertFalse(self.market.rows('reviews'));self.assertFalse(self.market.rows('movements',"kind='dismissal'"))
  self.market.simulation_settings=dict(enabled=True,cadence=7)
  self.advance(20260202,matches(10));self.assertEqual(10,len(self.market.rows('results')));self.assertTrue(all(r['game_date']==20260202 for r in self.market.rows('reviews')))
 def test_monthly_review_remembers_prior_days_but_never_rerolls_unchanged_campaign(self):
  from test_global_performance import native
  self.market.simulation_settings=dict(enabled=True,cadence=30)
  def observed(today,count):
   c=context(today);c['performance']=[native(1,today,count)];c['tables']={'100':[dict(club=i,played=count,points=count*3 if i==2 else 0,rank=j+1,gf=0,ga=0) for j,i in enumerate((2,3,1))]};c['table_dates']={'100':today};return c
  with patch('engine.draw',return_value=9999):
   for today,count in ((20260330,8),(20260331,9)):
    with self.market.db:self.market.advance(observed(today,count))
   self.assertTrue(self.market.rows('market_review_pending'));self.assertFalse(self.market.rows('reviews'))
   self.market.checkpoint('pending','DATA');self.market.open_save('pending','DATA',context(20260331))
   with self.market.db:self.market.advance(observed(20260401,9))
   self.assertEqual([20260401],[r['game_date'] for r in self.market.rows('reviews')]);self.assertFalse(self.market.rows('market_review_pending'))
   with self.market.db:self.market.advance(observed(20260501,9))
   self.assertEqual(1,len(self.market.rows('reviews')))
 def test_request_is_scoped_and_rejects_other_save_stale_token_and_bad_options(self):
  observed=dict(save=dict(pid=10,process_created_100ns=20),profile=dict(context_address=30,context_epoch=2,club_id=3),date=20260101);model=dict(profileToken='a'*64)
  def file(**overrides):
   fields=dict(schema=1,pid=10,created=20,context='1e',epoch=2,club=3,date=20260101,captured_tick=1000,wire='S16MGRS1|'+'a'*64+'|0|2|1|END');fields.update(overrides);path=self.root/'request.tsv';path.write_bytes(''.join(f'{k}={v}\n' for k,v in fields.items()).encode());return path
  self.assertEqual(dict(enabled=False,cadence=30),request(file(),observed,model,1100)['value'])
  for change in (dict(pid=11),dict(epoch=3),dict(context='1f'),dict(date=20260102),dict(captured_tick=-40000),dict(wire='S16MGRS1|'+'b'*64+'|0|2|1|END'),dict(wire='S16MGRS1|'+'a'*64+'|2|9|1|END')):
   with self.subTest(change=change),self.assertRaises(ValueError):request(file(**change),observed,model,1100)
 def test_native_mouse_switch_is_immediate_and_controller_keyboard_can_reach_selector(self):
  model=dict(project(self.market),profileToken='a'*64)
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=self.root/'settings.big';native_screen.build(test_screen.GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
  vm,s,_,calls=open_native(path,full=FULL);test_screen.load_data(vm,s)
  vm.invoke(s.get('Command'),s,(3,));self.assertTrue(s.get('scene5').get('_visible'));vm.invoke(s.get('Move'),s,(3,));self.assertEqual(400,s.get('focus'))
  s.set('_xmouse',1620);s.set('_ymouse',430);vm.invoke(s.get('onMouseDown'),s);self.assertFalse(s.get('marketEnabled'))
  events=[a for n,a in calls if n=='SendSystemEvent' and 'Server16ManagerSettings' in a];self.assertEqual(1,len(events));self.assertIn('|0|0|1|END',events[0][-1])
  vm.invoke(s.get('Move'),s,(3,));self.assertEqual(403,s.get('focus'));vm.invoke(s.get('Command'),s,(402,));self.assertEqual(1,s.get('cadenceIndex'))
  vm.invoke(s.get('Move'),s,(2,));self.assertEqual(400,s.get('focus'));vm.invoke(s.get('Move'),s,(2,));self.assertEqual(3,s.get('focus'));self.assertFalse(vm.errors)

if __name__=='__main__':unittest.main()
