import copy,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
import test_screen
sys.path.insert(0,str(test_screen.SOURCE/'club_browser'))
from test_engine import catalog,context,matches
from engine import Market
from model import project
from club_history import build as history,request as history_request
from career_profile import build as career
from title_rewards import reward,renewal_bonus
from PIL import Image
from screen import script_factory,scenes_for,FULL,stars
import native_screen
from native_review_vm import open_native

class RefinementsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'cat.db');self.market=Market(self.root/'world.db',self.root/'cat.db');self.market.open_save('initial','DATA',context())
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def advance(self,c):
  with self.market.db:self.market.advance(c)
 def native(self,model,assets=None):
  images={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)},'crest_1':Image.new('RGBA',(64,64),'red')};images.update(assets or {})
  path=self.root/'screen.big';native_screen.build(test_screen.GAME,path,scenes_for(model,images),images,script_factory=script_factory(model,images),full_name=FULL)
  vm,state,apt,calls=open_native(path,full=FULL);test_screen.load_data(vm,state);return vm,state,calls
 def test_one_arrow_click_even_after_holding_and_native_release_echo(self):
  vm,s,_=self.native(project(self.market));s.set('clubs',s.get('clubs')*9);vm.invoke(s.get('Command'),s,(0,))
  actions=scenes_for(project(self.market),{})[0]['actions'];index=next(i for i,a in enumerate(actions) if int(a['target'])==51);button=s.get('scene0').get('action'+str(index));box=actions[index]
  s.set('_xmouse',button.get('_x')+20);s.set('_ymouse',box['y']+15);vm.invoke(s.get('onMouseMove'),s);vm.invoke(s.get('onMouseDown'),s);self.assertEqual(1,s.get('page'))
  for _ in range(20):vm.invoke(s.get('ScrollFrame'),s)
  vm.invoke(s.get('LocalEventHandler'),s,(2,None));self.assertEqual(1,s.get('page'))
  vm.invoke(s.get('onMouseUp'),s);vm.invoke(s.get('LocalEventHandler'),s,(2,None));vm.invoke(s.get('LocalEventHandler'),s,(7,None));self.assertEqual(1,s.get('page'))
  for _ in range(6):vm.invoke(s.get('ScrollFrame'),s)
  vm.invoke(s.get('LocalEventHandler'),s,(2,None));vm.invoke(s.get('LocalEventHandler'),s,(7,None));self.assertEqual(2,s.get('page'));self.assertFalse(vm.errors)
 def test_departure_status_uses_real_exit_reason_and_merges_contract_renewals(self):
  person=dict(coach_id='coach');clubs={1:dict(name='Um'),2:dict(name='Dois')}
  def a(ident,club,start,end,reason,renewal=False):return dict(id=ident,coach_id='coach',club_id=club,start_date=start,end_date=end,end_reason=reason,origin='Mercado simulado',monthly_wage=1000,renewal=renewal)
  visits=[a('a',1,20260101,20260201,'renewed'),a('b',1,20260201,20260301,'resignation',True),a('c',2,20260401,20260501,'poached'),a('d',1,20260601,None,None)]
  moves=[dict(coach_id='coach',club_id=1,game_date=20260301,kind='resignation',reason='Treinador optou por não renovar ao término do contrato'),dict(coach_id='coach',club_id=2,game_date=20260501,kind='poached',reason='Saída · multa de 10000 paga por Um')]
  data=career(person,visits,[],[],{},clubs,20260701,str,movements=moves);self.assertEqual(['Atual','Saída com multa','Não renovou'],[s['status'] for s in data['spells']])
 def test_prestigious_title_raises_reference_salary_and_reputation_once_without_rewriting_contract(self):
  before=self.market.one('coaches','coach_id','2');contract=self.market.active(club=2)
  c=context(20260110,matches(3));c['competitions']=[dict(asset=100,name='Copa',prestige=9)];c['titles']=[dict(root=100,asset=100,club=2,date=20260110,season=20260101,name='Copa')]
  self.advance(c);after=self.market.one('coaches','coach_id','2');self.assertAlmostEqual(reward(9)[0],after['reputation']-before['reputation']);self.assertGreater(after['salary'],before['salary']);self.assertEqual(contract['monthly_wage'],self.market.active(club=2)['monthly_wage']);self.assertGreater(renewal_bonus(self.market,contract,20260110),0)
  self.advance(c);self.assertEqual(after,self.market.one('coaches','coach_id','2'));self.assertEqual(1,len(self.market.rows('honours')));self.assertGreater(reward(9)[0],reward(2)[0]);self.assertGreater(reward(9)[1],reward(2)[1])
 def populate_history(self):
  self.advance(context(20260120,matches(5)));self.market.leave(self.market.active(club=1),20260121,'dismissal','Campanha ruim');self.market.appoint(self.market.one('coaches','coach_id','4'),self.market.one('clubs','club_id',1),20260122,'hired')
  self.market.db.execute('UPDATE appointments SET contract_end=20290101 WHERE branch=? AND club_id=1 AND end_date IS NULL',(self.market.branch,))
  fixture=dict(matches(1)[0],id=1001,date=20270110,season=20270101,hg=2,ag=0)
  self.advance(dict(context(20270111,matches(5)+[fixture]),season=20270101))
  self.market.add('honours',dict(coach_id='4',club_id=1,season=20270101,competition_id=100,root=200,game_date=20270110,name='Copa'))
 def test_club_timeline_keeps_all_years_and_only_this_clubs_spells_after_reload(self):
  self.populate_history();model=project(self.market,lightweight=True);data=history(self.market,1,model['people']);self.assertEqual(2,len(data['rows']));self.assertEqual(['Atual','Demitido'],[r[4] for r in data['rows']]);self.assertEqual('5',data['rows'][1][5]);self.assertEqual('1',data['rows'][0][10]);self.assertIn('2026',data['rows'][1][2]);self.assertNotIn('Treinador 2',[r[0] for r in data['rows']])
  self.market.checkpoint('saved','DATA');self.market.open_save('saved','DATA',context(20270111));self.assertEqual(data,history(self.market,1,project(self.market,lightweight=True)['people']))
 def test_native_club_picker_requests_one_club_and_timeline_supports_back_and_profiles(self):
  self.populate_history();base=dict(project(self.market,lightweight=True),lazyProfiles=True,profileToken='a'*64);vm,s,calls=self.native(base);vm.invoke(s.get('Command'),s,(3,));self.assertTrue(s.get('scene6').get('_visible'));vm.invoke(s.get('Command'),s,(40,));self.assertTrue(s.get('historyPending'))
  wire=next(a[-1] for n,a in calls if n=='SendSystemEvent' and 'Server16ClubHistory' in a);fields=dict(schema=1,pid=10,created=20,club=3,context='1e',epoch=2,date=20270111,captured_tick=1000,wire=wire);path=self.root/'request.tsv';path.write_text(''.join(f'{k}={v}\n' for k,v in fields.items()))
  observed=dict(save=dict(pid=10,process_created_100ns=20),profile=dict(club_id=3,context_address=30,context_epoch=2),date=20270111);click=history_request(path,observed,base,1100)
  loaded=dict(base,clubHistory=history(self.market,click['club'],base['people']),resume=click['resume']);vm,s,calls=self.native(loaded);self.assertTrue(s.get('scene7').get('_visible'));self.assertEqual(2,len(s.get('timelineRows')));vm.invoke(s.get('Move'),s,(3,));self.assertEqual(541,s.get('focus'));vm.invoke(s.get('Command'),s,(60,));self.assertTrue(s.get('scene6').get('_visible'));self.assertFalse(vm.errors)
 def test_title_card_displays_club_crest_real_cup_and_has_no_explanatory_filler(self):
  model=project(self.market);person=model['clubRows'][0][7];model['people'][person]['titleCards']=[['Copa','competition_100','Clube 1','crest_1','2026','10/01/2026']]
  vm,s,_=self.native(model,dict(competition_100=Image.new('RGBA',(64,64),'yellow'),cup_100=Image.new('RGBA',(64,64),'gold')));vm.invoke(s.get('Command'),s,(40,));vm.invoke(s.get('Command'),s,(82,));clip=s.get('scene1')
  self.assertEqual('Clube 1',clip.get('entryTotal0').get('text'));self.assertTrue(clip.get('entry0_crest_1').get('_visible'));self.assertTrue(clip.get('cup0_cup_100').get('_visible'));self.assertFalse(vm.errors)
 def test_current_coach_comes_first_when_predecessor_left_on_same_start_day(self):
  data=history(self.market,3,project(self.market,lightweight=True)['people']);self.assertEqual('Atual',data['rows'][0][4]);self.assertEqual('Substituído',data['rows'][1][4])
 def test_long_timeline_supports_controller_scrolling_and_mouse_track(self):
  model=project(self.market);data=history(self.market,3,model['people']);data['rows']=data['rows']*3;model.update(clubHistory=data,resume=dict(tab=3,clubTimeline=True,focus=540))
  vm,s,_=self.native(model);self.assertEqual(4,s.get('timelinePageCount'))
  for _ in range(3):vm.invoke(s.get('Move'),s,(3,))
  self.assertEqual(1,s.get('timelinePage'));s.set('frames',s.get('frames')+6);vm.invoke(s.get('LocalEventHandler'),s,(9,None));self.assertEqual(2,s.get('timelinePage'))
  s.set('_xmouse',1824);s.set('_ymouse',365);vm.invoke(s.get('onMouseDown'),s);self.assertEqual(0,s.get('timelinePage'));vm.invoke(s.get('onMouseUp'),s);self.assertFalse(vm.errors)
 def test_league_country_preference_handles_cross_border_clubs_and_localized_names(self):
  from hiring_fit import league_nationalities
  from engine import nationalities
  clubs={i:dict(league_id=50,country='Brazil' if i<4 else 'Argentina') for i in range(1,5)}
  self.assertEqual(nationalities('Brasil RS'),league_nationalities(clubs[4],clubs,nationalities))
  clubs[3]['league_id']=51;self.assertEqual(nationalities('Brazil'),league_nationalities(clubs[4],clubs,nationalities))

if __name__=='__main__':unittest.main()
