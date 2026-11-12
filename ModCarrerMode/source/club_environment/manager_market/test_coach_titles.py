import copy,tempfile,unittest
from pathlib import Path
from coach_titles import canonical,read
from engine import Market
from test_engine import catalog,context,matches


class CoachTitlesTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.db')
  self.market=Market(self.root/'world.db',self.root/'catalog.db');self.market.open_save('save','DATA',context())
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def title(self,**changes):
  return dict(dict(coach_id='1',club_id=1,season=20260101,competition_id=100,root=100,game_date=20260110,name='Copa'),**changes)
 def gallery(self,**changes):
  self.market.add('trophy_history',dict(self.title(**changes),source='confirmed_calendar',team_kind='club'))
 def test_dated_event_is_unique_even_when_activation_day_changes_season_key(self):
  old=self.title(season=20260109,name='Competição 100');new=self.title(source='confirmed_calendar')
  rows=canonical([old,new],20260110);self.assertEqual(1,len(rows));self.assertEqual('Copa',rows[0]['name'])
 def test_different_years_and_competition_roots_remain_distinct(self):
  rows=canonical([self.title(),self.title(season=20270101,game_date=20270110),self.title(root=200)],20270110)
  self.assertEqual(3,len(rows));self.assertEqual(20270110,rows[0]['game_date'])
 def test_future_and_invalid_dates_are_not_trophies(self):
  self.assertEqual([],canonical([self.title(game_date=20270230),self.title(game_date=20270110)],20261231))
 def test_selected_cv_merges_gallery_only_honours_and_legacy_rows(self):
  self.market.add('honours',self.title(season=20260109));self.gallery()
  self.gallery(competition_id=101,root=101,game_date=20260111,name='Recopa')
  rows=read(self.market,'1',20260112);self.assertEqual(2,len(rows));self.assertEqual('Recopa',rows[0]['name'])
  self.assertEqual([],read(self.market,'2',20260112))
 def test_confirmed_owner_prevents_a_stale_honour_appearing_for_two_coaches(self):
  self.market.add('honours',self.title());self.gallery(coach_id='2')
  self.assertEqual([],read(self.market,'1',20260112));self.assertEqual(1,len(read(self.market,'2',20260112)))
 def test_duplicate_season_cannot_pay_a_second_salary_or_reputation_bonus(self):
  self.market.add('honours',self.title(coach_id='2',club_id=2,season=20260109))
  before=self.market.one('coaches','coach_id','2')
  value=context(20260110,matches(3));value['titles']=[dict(root=100,asset=100,club=2,date=20260110,season=20260101,name='Copa')]
  with self.market.db:self.market.advance(value)
  after=self.market.one('coaches','coach_id','2');self.assertEqual(before['reputation'],after['reputation']);self.assertEqual(before['salary'],after['salary'])
  self.assertEqual(1,len(self.market.rows('honours')))
 def test_profile_keeps_trophy_with_the_coach_in_charge_on_the_award_date(self):
  from career_profile import build
  visit=dict(id='a',coach_id='1',club_id=1,start_date=20260111,end_date=None,end_reason=None,origin='Mercado simulado',monthly_wage=1000)
  rich=build(dict(coach_id='1'),[visit],[],[self.title()],{}, {1:dict(name='Um')},20260120,str)
  self.assertEqual([],rich['titles']);self.assertEqual(0,rich['spells'][0]['titles'])


class TitleTimelineTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import test_screen as fixture
  from PIL import Image
  from model import project
  from screen import scenes_for,script_factory,FULL,stars
  import native_screen
  cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name);catalog(root/'cat.db')
  market=Market(root/'world.db',root/'cat.db');market.open_save('save','DATA',context())
  model=project(market);market.close();p=model['people'][model['clubRows'][0][7]]
  p['titleCards']=[[f'Copa {i}','competition_100','Clube 1','crest_1','2027' if i<4 else '2026',f'{20-i:02d}/10/2027',f'Conquistado em {20-i:02d}/10/2027'] for i in range(8)]
  assets={key:Image.new('RGBA',(64,64),color) for key,color in [('head_NOTFOUND_DEFAULT','gray'),('crest_1','red'),('competition_100','yellow'),('cup_100','gold')]}
  assets.update({'stars_'+str(i):stars(i) for i in range(11)})
  cls.package=root/'titles.big';native_screen.build(fixture.GAME,cls.package,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def open(self):
  import test_screen as fixture
  from native_review_vm import open_native
  from screen import FULL
  vm,s,_,_=open_native(self.package,full=FULL);fixture.load_data(vm,s)
  vm.invoke(s.get('Command'),s,(40,));vm.invoke(s.get('Command'),s,(82,));return vm,s,s.get('scene1')
 def test_cards_have_distinct_trophy_competition_club_and_year_slots(self):
  vm,s,c=self.open();self.assertEqual('Copa 0',c.get('titleName0').get('text'));self.assertEqual('Clube 1',c.get('titleClub0').get('text'))
  for name in ('titleCup0_cup_100','titleCompetition0_competition_100','titleCrest0_crest_1'):self.assertTrue(c.get(name).get('_visible'))
  self.assertEqual('2027',c.get('titleYear0').get('text'));self.assertFalse(c.get('entryCard0').get('_visible'))
  self.assertEqual('1–3 de 8 títulos',c.get('historyPage').get('text').encode('latin1').decode('utf8'));self.assertFalse(vm.errors)
 def test_wheel_and_keyboard_scroll_one_record_and_switching_tabs_hides_titles(self):
  vm,s,c=self.open();vm.invoke(s.get('onMouseWheel'),s,(-1,));self.assertEqual(1,s.get('historyPage'))
  vm.invoke(s.get('Move'),s,(3,));self.assertEqual(2,s.get('historyPage'));self.assertEqual('Copa 2',c.get('titleName0').get('text'))
  vm.invoke(s.get('Command'),s,(81,));self.assertFalse(c.get('titleCard0').get('_visible'));self.assertFalse(c.get('titleTimelineRail').get('_visible'));self.assertFalse(vm.errors)
 def test_scrollbar_grab_does_not_jump_and_reaches_the_last_three_titles(self):
  vm,s,c=self.open();s.set('_xmouse',1826);s.set('_ymouse',335);vm.invoke(s.get('onMouseDown'),s)
  self.assertEqual(0,s.get('historyPage'));s.set('_ymouse',845);vm.invoke(s.get('onMouseMove'),s);vm.invoke(s.get('onMouseUp'),s)
  self.assertEqual(5,s.get('historyPage'));self.assertEqual('Copa 5',c.get('titleName0').get('text'));self.assertEqual('6–8 de 8 títulos',c.get('historyPage').get('text').encode('latin1').decode('utf8'));self.assertEqual(0,s.get('dragScroll'));self.assertFalse(vm.errors)
 def test_large_history_keeps_a_grabbable_thumb_and_short_history_hides_it(self):
  vm,s,c=self.open();person=s.get('people')[s.get('person')];person[25]=person[25]*15;vm.invoke(s.get('Refresh'),s)
  self.assertGreaterEqual(c.get('historyScrollThumb').get('_height'),48)
  person[25]=person[25][:2];vm.invoke(s.get('Command'),s,(82,));self.assertFalse(c.get('historyScrollThumb').get('_visible'));self.assertEqual('1–2 de 2 títulos',c.get('historyPage').get('text').encode('latin1').decode('utf8'));self.assertFalse(vm.errors)


if __name__=='__main__':unittest.main()
