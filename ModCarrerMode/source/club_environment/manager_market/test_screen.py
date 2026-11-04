from pathlib import Path
import copy,inspect,os,sys,tempfile,unittest
GAME=Path(__file__).resolve().parents[4];SOURCE=GAME/'ModCarrerMode/source';ENV=SOURCE/'club_environment'
os.environ['SERVER16_GAME_ROOT']=str(GAME)
sys.path[:0]=[str(SOURCE),str(ENV),str(ENV/'vendor'),str(ENV/'bank'),str(ENV/'preview'),str(ENV/'market')]
from PIL import Image
from engine import Market
from test_engine import catalog,context
from model import project
from screen import scenes_for,script_factory,stars,FULL,waiting
import native_screen
from native_review_vm import open_native
from apt_vm import VM,Object
from unittest.mock import patch

def load_data(vm,state):
 for _ in range(1000):
  if state.get('dataReady'):return
  vm.invoke(state.get('DataFrame'),state)
 raise AssertionError('Native data loader did not finish')

class NativeScreenTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name);catalog(root/'cat.sqlite3');m=Market(root/'world.sqlite3',root/'cat.sqlite3');m.open_save('one','DATA',context());cls.model=project(m);m.close()
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)},**{'crest_'+str(i):Image.new('RGBA',(48,48),'red') for i in range(1,4)}}
  cls.package=root/'managers.big';native_screen.build(GAME,cls.package,scenes_for(cls.model,assets),assets,script_factory=script_factory(cls.model,assets),full_name=FULL)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def open(self):
  vm,s,apt,calls=open_native(self.package,full=FULL);load_data(vm,s);return vm,s,calls
 def test_large_catalog_native_stack_stays_bounded(self):
  model=copy.deepcopy(self.model);model['people']=(model['people']*100)[:2100];model['clubRows']=(model['clubRows']*700)[:2100]
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'large.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
  lines,start=inspect.getsourcelines(VM.run);observed=next(start+i for i,l in enumerate(lines) if 'self.steps+=1' in l);metrics={'peak_stack':0}
  def trace(frame,event,arg):
   if frame.f_code!=VM.run.__code__:return None
   if event=='line' and frame.f_lineno==observed:
    used=len(frame.f_locals.get('stack',[]));metrics['peak_stack']=max(metrics['peak_stack'],used)
    if used>128:raise AssertionError('Native APT operand stack exceeds 128: '+str(used))
   return trace
  previous=sys.gettrace();sys.settrace(trace)
  try:vm,state,_,_=open_native(path,full=FULL);load_data(vm,state)
  finally:sys.settrace(previous)
  self.assertEqual(2100,len(state.get('people')));self.assertEqual(2100,len(state.get('clubs')));self.assertLessEqual(metrics['peak_stack'],128)
 def test_lists_tabs_and_immediate_age_nationality_filters(self):
  vm,s,calls=self.open();self.assertEqual(3,len(s.get('filtered')));vm.invoke(s.get('Command'),s,(2,));self.assertGreater(len(s.get('filtered')),0);before=s.get('age');vm.invoke(s.get('Command'),s,(35,));self.assertNotEqual(before,s.get('age'));self.assertEqual(0,len(s.get('filtered')));vm.invoke(s.get('Command'),s,(37,));self.assertEqual(1,s.get('nation'))
 def test_one_mouse_click_and_native_select_echo_advance_exactly_one_country(self):
  vm,s,_=self.open();s.set('countries',[[name,'flag_0'] for name in ('Brasil','Dinamarca','Espanha','França')]);s.set('leagues',[[i,name,name,1,'league_1',name] for i,name in enumerate(('Brasil','Dinamarca','Espanha','França'))]);s.set('country',0);s.set('league',0)
  vm.invoke(s.get('Refresh'),s);s.set('_xmouse',430);s.set('_ymouse',380);s.set('focus',11)
  for expected in (1,2,3,0):
   vm.invoke(s.get('onMouseDown'),s);vm.invoke(s.get('onMouseUp'),s)
   vm.invoke(s.get('LocalEventHandler'),s,(2,None));vm.invoke(s.get('LocalEventHandler'),s,(7,None))
   self.assertEqual(expected,s.get('country'));self.assertEqual(expected,s.get('league'))
  for _ in range(4):vm.invoke(s.get('ScrollFrame'),s)
  vm.invoke(s.get('LocalEventHandler'),s,(2,None));self.assertEqual(1,s.get('country'));self.assertEqual([],vm.errors)
 def test_open_profile_back_and_native_exit(self):
  vm,s,calls=self.open();vm.invoke(s.get('Command'),s,(40,));self.assertTrue(s.get('profile'));vm.invoke(s.get('Command'),s,(60,));self.assertFalse(s.get('profile'));vm.invoke(s.get('Command'),s,(60,));self.assertTrue(any(n=='SendEvent' and 'Back' in args for n,args in calls))
 def test_mouse_clicks_cards_through_art_and_ignores_hidden_scenes(self):
  vm,s,_=self.open();rendered=s.get('rendered');box=next(v for v in scenes_for(self.model,{})[0]['actions'] if int(v['target'])==40)
  s.set('_xmouse',box['x']+box['w']/2);s.set('_ymouse',box['y']+box['h']/2);vm.invoke(s.get('onMouseMove'),s)
  self.assertIs(s.get('rendered'),rendered);self.assertEqual(40,s.get('focus'))
  vm.invoke(s.get('onMouseDown'),s);self.assertTrue(s.get('profile'));self.assertEqual(s.get('person'),self.model['clubRows'][0][7])
  vm.invoke(s.get('Command'),s,(60,));s.set('_xmouse',-1);vm.invoke(s.get('onMouseDown'),s);self.assertFalse(s.get('profile'));self.assertEqual([],vm.errors)
 def test_club_dots_follow_the_current_page(self):
  vm,s,_=self.open();s.set('clubs',s.get('clubs')*7);vm.invoke(s.get('Command'),s,(0,))
  self.assertEqual(s.get('pageCount'),4);clip=s.get('scene0');self.assertTrue(clip.get('pageDotOn0').get('_visible'))
  vm.invoke(s.get('Command'),s,(51,));self.assertTrue(clip.get('pageDotOn1').get('_visible'));self.assertFalse(clip.get('pageDotOn0').get('_visible'));self.assertTrue(clip.get('pageDotOff0').get('_visible'));self.assertEqual(vm.errors,[])
 def test_dots_are_clickable_and_history_years_are_separate_from_spells(self):
  vm,s,_=self.open();s.set('clubs',s.get('clubs')*7);vm.invoke(s.get('Command'),s,(0,))
  s.set('_xmouse',1100+2*19);s.set('_ymouse',926);vm.invoke(s.get('onMouseDown'),s);self.assertEqual(2,s.get('page'))
  vm.invoke(s.get('Command'),s,(40,));vm.invoke(s.get('Command'),s,(84,));self.assertEqual(4,s.get('profileTab'));self.assertEqual([],vm.errors)
 def test_movement_scroll_supports_track_click_drag_and_release(self):
  vm,s,_=self.open();row=list(self.model['hireRows'][0]) if self.model['hireRows'] else list(self.model['clubRows'][0])+[20260102,'02/01/2026','Brasil'];row[9]=self.model['months'][s.get('month')][0]*100+2
  row=row[:11]+[s.get('countries')[0][0]];s.set('hires',[row]*15);vm.invoke(s.get('Command'),s,(1,));s.set('_xmouse',947);s.set('_ymouse',830);vm.invoke(s.get('onMouseDown'),s)
  self.assertGreater(s.get('hirePage'),0);s.set('_ymouse',438);vm.invoke(s.get('onMouseMove'),s);self.assertEqual(0,s.get('hirePage'))
  vm.invoke(s.get('onMouseUp'),s);self.assertEqual(0,s.get('dragScroll'));self.assertEqual([],vm.errors)
 def test_movement_league_filter_preserves_month_and_filters_both_lists(self):
  vm,s,_=self.open();row=list(self.model['clubRows'][0])+[self.model['months'][s.get('month')][0]*100+2,'02/01/2026'];row[8]=s.get('leagues')[0][0]
  other=list(row);other[8]=-1;s.set('hires',[row,other]);s.set('moves',[row,other]);vm.invoke(s.get('Command'),s,(1,));s.set('movementCountry',0);s.set('movementLeague',0);vm.invoke(s.get('Refresh'),s);month=s.get('month')
  self.assertEqual(2,len(s.get('monthHires')));vm.invoke(s.get('Command'),s,(23,));self.assertEqual(1,len(s.get('monthHires')));self.assertEqual(1,len(s.get('monthMoves')));self.assertEqual(month,s.get('month'));self.assertEqual([],vm.errors)
 def test_native_scroll_press_and_frame_drag_do_not_require_global_mouse_events(self):
  vm,s,_=self.open();row=list(self.model['clubRows'][0])+[self.model['months'][s.get('month')][0]*100+2,'02/01/2026','Brasil'];s.set('hires',[row]*15);vm.invoke(s.get('Command'),s,(1,))
  boxes=scenes_for(self.model,{})[3]['actions'];i=next(i for i,b in enumerate(boxes) if b['target']=='200');button=s.get('scene3').get('action'+str(i))
  s.set('_ymouse',820);vm.invoke(button.get('onPress'),button);self.assertEqual(1,s.get('dragScroll'));self.assertGreater(s.get('hirePage'),0)
  s.set('_ymouse',438);vm.invoke(s.get('ScrollFrame'),s);self.assertEqual(0,s.get('hirePage'));vm.invoke(button.get('onReleaseOutside'),button);self.assertEqual(0,s.get('dragScroll'));self.assertEqual([],vm.errors)
 def test_country_and_league_filters_are_separate_and_reset_dependent_selection(self):
  vm,s,_=self.open();row=list(self.model['clubRows'][0])+[self.model['months'][s.get('month')][0]*100+2,'02/01/2026',s.get('countries')[0][0]];other=list(row);other[11]='Outro país';s.set('hires',[row,other]);vm.invoke(s.get('Command'),s,(1,));s.set('movementCountry',0);vm.invoke(s.get('Command'),s,(25,))
  self.assertEqual(1,len(s.get('monthHires')));self.assertEqual(0,s.get('movementLeague'));self.assertEqual(s.get('countries')[0][0],s.get('scene3').get('movementCountry').get('text'));self.assertEqual([],vm.errors)
 def test_spatial_navigation_tabs_filters_and_card_rows(self):
  vm,s,_=self.open()
  s.set('focus',0);vm.invoke(s.get('Move'),s,(3,));self.assertEqual(s.get('focus'),10);self.assertEqual(s.get('tab'),0)
  vm.invoke(s.get('Move'),s,(3,));self.assertEqual(s.get('focus'),20)
  vm.invoke(s.get('Move'),s,(3,));self.assertEqual(s.get('focus'),40)
  vm.invoke(s.get('Move'),s,(1,));self.assertEqual(s.get('focus'),41)
  vm.invoke(s.get('Move'),s,(0,));self.assertEqual(s.get('focus'),40)
  vm.invoke(s.get('Move'),s,(3,));self.assertEqual(s.get('focus'),42)
  vm.invoke(s.get('Command'),s,(2,));s.set('focus',2);vm.invoke(s.get('Move'),s,(3,));self.assertEqual(s.get('focus'),36);self.assertEqual(s.get('tab'),2);self.assertEqual(vm.errors,[])
 def test_history_scroll_uses_overall_results_and_visible_thumb(self):
  vm,s,_=self.open();vm.invoke(s.get('Command'),s,(40,));person=s.get('people')[s.get('person')]
  row=person[24][0];person[24]=[list(row) for _ in range(5)]
  vm.invoke(s.get('Command'),s,(81,));self.assertEqual(s.get('historyPages'),3)
  vm.invoke(s.get('Command'),s,(71,));self.assertEqual(s.get('historyPage'),1)
  clip=s.get('scene1');self.assertTrue(clip.get('historyScrollThumb').get('_visible'));self.assertRegex(clip.get('entryHome0').get('text'),r'^\d+,\d%$');self.assertTrue(clip.get('entryValue0_0').get('_visible'));self.assertFalse(clip.get('entryAway0').get('_visible'));self.assertEqual(vm.errors,[])
 def test_month_filters_open_current_month_and_ignore_duplicate_press(self):
  model=copy.deepcopy(self.model);model['months']=[[202610,'Outubro 2026'],[202611,'Novembro 2026'],[202612,'Dezembro 2026']];model['initialMonth']=2
  package=Path(self.tmp.name)/'monthly.big';native_screen.build(GAME,package,scenes_for(model,{}),{},script_factory=script_factory(model,{}),full_name=FULL)
  vm,s,_,calls=open_native(package,full=FULL);load_data(vm,s);vm.invoke(s.get('Command'),s,(1,));self.assertEqual(2,s.get('month'))
  vm.invoke(s.get('LocalEventHandler'),s,(8,None));vm.invoke(s.get('LocalEventHandler'),s,(8,None));self.assertEqual(1,s.get('month'))
  for _ in range(6):vm.invoke(s.get('ScrollFrame'),s)
  vm.invoke(s.get('Command'),s,(30,));self.assertEqual(0,s.get('month'))
  vm.invoke(s.get('Command'),s,(31,));self.assertEqual(1,s.get('month'));self.assertEqual([],vm.errors)
 def test_initial_view_defers_unopened_coach_histories(self):
  vm,s,_=self.open();self.assertTrue(all(not person[23] and not person[24] for person in s.get('people')))
  vm.invoke(s.get('Command'),s,(40,));selected=s.get('person')
  self.assertTrue(s.get('people')[selected][23]);self.assertTrue(s.get('profileLoaded')[selected])
  self.assertTrue(all(not person[23] for i,person in enumerate(s.get('people')) if i!=selected))
 def test_loader_callbacks_do_not_collide_with_state_in_legacy_member_lookup(self):
  def get(obj,key):
   if isinstance(key,str):
    own=next((k for k in obj.values if isinstance(k,str) and k.casefold()==key.casefold()),None)
    if own is not None:return obj.values[own]
   elif key in obj.values:return obj.values[key]
   return obj.prototype.get(key) if obj.prototype else None
  def set_value(obj,key,value):
   if isinstance(key,str):key=next((k for k in obj.values if isinstance(k,str) and k.casefold()==key.casefold()),key)
   obj.values[key]=value
  with patch.object(Object,'get',get),patch.object(Object,'set',set_value):
   vm,s,_,calls=open_native(self.package,full=FULL);load_data(vm,s)
   self.assertTrue(s.get('dataReady'));self.assertTrue(s.get('inputBound'));self.assertTrue(s.get('scene0').get('_visible'));self.assertEqual([],vm.errors)
 def test_profile_tabs_metrics_and_pagination_use_structured_career_data(self):
  vm,s,calls=self.open();vm.invoke(s.get('Command'),s,(40,));clip=s.get('scene1');person=s.get('people')[s.get('person')]
  self.assertEqual(float(person[23][0]),float(clip.get('metric0').get('text')));self.assertTrue(clip.get('identityCard').get('_visible'))
  vm.invoke(s.get('Command'),s,(81,));self.assertEqual(1,s.get('profileTab'));self.assertFalse(clip.get('metricCard0').get('_visible'));self.assertTrue(clip.get('entryCard0').get('_visible'));self.assertEqual(person[24][0][0],clip.get('entryName0').get('text'));self.assertTrue(clip.get('current_crest_'+str(self.model['clubRows'][0][4].split('_')[-1])).get('_visible') if self.model['clubRows'][0][4] else True)
  vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(2,s.get('profileTab'));self.assertEqual(0,s.get('tab'));self.assertTrue(clip.get('emptyProfile').get('_visible'));self.assertEqual([],vm.errors)
 def test_reference_profile_has_functional_recent_filters_and_fourth_tab(self):
  model=copy.deepcopy(self.model);p=model['people'][model['clubRows'][0][7]];p['visualData'][9:12]=['VEDVVDEVEV','VVDEV','EDVEE'];p['visualData'][26]='profile_pitch_4_3_3';p['visualData'][24]='4-3-3';p['visualData'][4]='1,3 por jogo'
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),'profile_pitch_4_3_3':Image.new('RGBA',(440,430),'green'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'reference.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL);vm,s,_,_=open_native(path,full=FULL);load_data(vm,s);vm.invoke(s.get('Command'),s,(40,));clip=s.get('scene1')
  self.assertEqual('VEDVVDEVEV',s.get('profileRecent'));self.assertTrue(clip.get('recent0_V').get('_visible'));self.assertTrue(clip.get('metricIcon2').get('_visible'));self.assertEqual(p['visualData'][4],clip.get('metricNote4').get('text'))
  vm.invoke(s.get('Command'),s,(90,));self.assertEqual('Em casa',clip.get('filterName').get('text'));self.assertEqual('VVDEV',s.get('profileRecent'));self.assertFalse(clip.get('recent5_D').get('_visible'));self.assertFalse(clip.get('recentLetter5').get('_visible'))
  vm.invoke(s.get('LocalEventHandler'),s,(4,None));self.assertEqual('EDVEE',s.get('profileRecent'));vm.invoke(s.get('Command'),s,(83,));self.assertEqual(3,s.get('profileTab'));self.assertIsNone(clip.get('formationCard'))
  vm.invoke(s.get('Command'),s,(83,));vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(4,s.get('profileTab'));vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(0,s.get('profileTab'));self.assertEqual([],vm.errors)
 def test_profile_long_history_and_trophies_have_independent_pages_and_artwork(self):
  model=copy.deepcopy(self.model);p=model['people'][model['clubRows'][0][7]];p['spellCards']=[[f'Clube {i}','crest_1',f'01/01/202{i} → Atual','30 dias no cargo','Atual','2 J · 1 V · 1 E · 0 D',66.7,'2 J · 1 V · 1 E · 0 D',66.7,'0 J',0,'1 título'] for i in range(7)];p['titleCards']=[[f'Liga {i}','competition_7','Clube 1','crest_1','2026','10/01/2026'] for i in range(4)]
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),'competition_7':Image.new('RGBA',(64,64),'yellow'),'crest_1':Image.new('RGBA',(64,64),'red'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'long-history.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL);vm,s,_,_=open_native(path,full=FULL);load_data(vm,s);vm.invoke(s.get('Command'),s,(40,));vm.invoke(s.get('Command'),s,(81,));clip=s.get('scene1');self.assertEqual(5,s.get('historyPages'));vm.invoke(s.get('Command'),s,(71,));self.assertEqual('Clube 1',clip.get('entryName0').get('text'));vm.invoke(s.get('Command'),s,(71,));self.assertEqual('Clube 2',clip.get('entryName0').get('text'));self.assertTrue(clip.get('entryCard1').get('_visible'))
  vm.invoke(s.get('Command'),s,(82,));self.assertEqual(0,s.get('historyPage'));self.assertEqual(2,s.get('historyPages'));self.assertEqual('Liga 0',clip.get('entryName0').get('text'));self.assertTrue(clip.get('trophy0_competition_7').get('_visible'));self.assertFalse(clip.get('entry0_crest_1').get('_visible'));vm.invoke(s.get('Command'),s,(71,));self.assertEqual('Liga 1',clip.get('entryName0').get('text'));vm.invoke(s.get('Command'),s,(80,));self.assertFalse(clip.get('entryCard0').get('_visible'));self.assertEqual([],vm.errors)
 def test_controller_tabs_and_pages_stay_in_bounds(self):
  vm,s,calls=self.open();vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(1,s.get('tab'));self.assertEqual([],s.get('monthMoves'));self.assertEqual([],s.get('monthHires'));vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(2,s.get('tab'));vm.invoke(s.get('Command'),s,(2,));vm.invoke(s.get('Command'),s,(51,));self.assertEqual(1,s.get('page'));vm.invoke(s.get('Command'),s,(50,));self.assertEqual(0,s.get('page'));vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(0,s.get('tab'))
 def test_movements_share_month_but_have_independent_pages_and_profiles(self):
  model=copy.deepcopy(self.model);model['months']=[[202512,'Dezembro 2025'],[202601,'Janeiro 2026'],[202602,'Fevereiro 2026']];model['initialMonth']=2
  r=model['clubRows'][0];model['moveRows']=[[*r,20260115,'15/01/2026','Brasil']];model['hireRows']=[[*r,20260116,'16/01/2026','Brasil'] for _ in range(5)]+[[*r,20260203,'03/02/2026','Brasil']]
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'movements.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
  vm,s,_,_=open_native(path,full=FULL);load_data(vm,s);vm.invoke(s.get('Command'),s,(1,));self.assertEqual(1,len(s.get('monthHires')));self.assertEqual(0,len(s.get('monthMoves')))
  vm.invoke(s.get('LocalEventHandler'),s,(8,None));self.assertEqual(1,s.get('tab'));self.assertEqual(5,len(s.get('monthHires')));self.assertEqual(1,len(s.get('monthMoves')));self.assertEqual(2,s.get('hirePageCount'));vm.invoke(s.get('Command'),s,(53,));self.assertEqual(1,s.get('hirePage'));self.assertEqual(0,s.get('movePage'));self.assertTrue(s.get('scene3').get('h_scrollThumb').get('_visible'));self.assertLess(s.get('scene3').get('h_scrollThumb').get('_height'),440)
  vm.invoke(s.get('Command'),s,(44,));self.assertTrue(s.get('profile'));self.assertEqual(r[7],s.get('person'));vm.invoke(s.get('Command'),s,(60,));s.set('frames',s.get('frames')+6);vm.invoke(s.get('Command'),s,(30,));self.assertEqual([],s.get('monthHires'));self.assertEqual([],s.get('monthMoves'));self.assertEqual(0,s.get('hirePage'));vm.invoke(s.get('Command'),s,(32,));self.assertEqual(0,s.get('month'));self.assertEqual([],vm.errors)
 def test_repeated_nationality_flags_and_reputation_have_separate_clips(self):
  model=copy.deepcopy(self.model)
  for p in model['people']:p['flag']='flag_54'
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),'flag_54':Image.new('RGBA',(64,40),'green'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'flags.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
  vm,s,_,_=open_native(path,full=FULL);load_data(vm,s)
  for slot in range(3):self.assertTrue(s.get('scene0').get('c_flag'+str(slot)+'_flag_54').get('_visible'))
  vm.invoke(s.get('Command'),s,(2,))
  for slot in range(6):self.assertTrue(s.get('scene4').get('f_flag'+str(slot)+'_flag_54').get('_visible'))
  vm.invoke(s.get('Command'),s,(40,));self.assertTrue(s.get('scene1').get('img_flag_54').get('_visible'));self.assertEqual([],vm.errors)
 def test_waiting_view_keeps_loading_and_back_available_without_null_league(self):
  model=waiting();assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}};path=Path(self.tmp.name)/'waiting.big'
  native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL);vm,s,_,calls=open_native(path,full=FULL);load_data(vm,s)
  self.assertTrue(s.get('scene2').get('_visible'));self.assertFalse(s.get('scene0').get('_visible'));vm.invoke(s.get('Command'),s,(2,));self.assertEqual(0,s.get('tab'));vm.invoke(s.get('Command'),s,(60,));self.assertTrue(any(name=='SendEvent' and 'Back' in args for name,args in calls));self.assertEqual([],vm.errors)

if __name__=='__main__':unittest.main()
