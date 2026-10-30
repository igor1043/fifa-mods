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
 def test_open_profile_back_and_native_exit(self):
  vm,s,calls=self.open();vm.invoke(s.get('Command'),s,(40,));self.assertTrue(s.get('profile'));vm.invoke(s.get('Command'),s,(60,));self.assertFalse(s.get('profile'));vm.invoke(s.get('Command'),s,(60,));self.assertTrue(any(n=='SendEvent' and 'Back' in args for n,args in calls))
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
  vm.invoke(s.get('LocalEventHandler'),s,(4,None));self.assertEqual('EDVEE',s.get('profileRecent'));vm.invoke(s.get('Command'),s,(83,));self.assertEqual(3,s.get('profileTab'));self.assertTrue(clip.get('formationCard').get('_visible'));self.assertTrue(clip.get('tactic_profile_pitch_4_3_3').get('_visible'));self.assertFalse(clip.get('summaryCard').get('_visible'));self.assertFalse(clip.get('entryCard0').get('_visible'));self.assertFalse(clip.get('recentEmpty').get('_visible'))
  vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(0,s.get('profileTab'));self.assertFalse(clip.get('tactic_profile_pitch_4_3_3').get('_visible'));self.assertEqual([],vm.errors)
 def test_profile_long_history_and_trophies_have_independent_pages_and_artwork(self):
  model=copy.deepcopy(self.model);p=model['people'][model['clubRows'][0][7]];p['spellCards']=[[f'Clube {i}','crest_1',f'01/01/202{i} → Atual','30 dias no cargo','Atual','2 J · 1 V · 1 E · 0 D',66.7,'2 J · 1 V · 1 E · 0 D',66.7,'0 J',0,'1 título'] for i in range(7)];p['titleCards']=[[f'Liga {i}','competition_7','Clube 1','crest_1','2026','10/01/2026'] for i in range(4)]
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),'competition_7':Image.new('RGBA',(64,64),'yellow'),'crest_1':Image.new('RGBA',(64,64),'red'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'long-history.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL);vm,s,_,_=open_native(path,full=FULL);load_data(vm,s);vm.invoke(s.get('Command'),s,(40,));vm.invoke(s.get('Command'),s,(81,));clip=s.get('scene1');self.assertEqual(3,s.get('historyPages'));vm.invoke(s.get('Command'),s,(71,));self.assertEqual('Clube 3',clip.get('entryName0').get('text'));vm.invoke(s.get('Command'),s,(71,));self.assertEqual('Clube 6',clip.get('entryName0').get('text'));self.assertFalse(clip.get('entryCard1').get('_visible'))
  vm.invoke(s.get('Command'),s,(82,));self.assertEqual(0,s.get('historyPage'));self.assertEqual(2,s.get('historyPages'));self.assertEqual('Liga 0',clip.get('entryName0').get('text'));self.assertTrue(clip.get('trophy0_competition_7').get('_visible'));self.assertFalse(clip.get('entry0_crest_1').get('_visible'));vm.invoke(s.get('Command'),s,(71,));self.assertEqual('Liga 3',clip.get('entryName0').get('text'));vm.invoke(s.get('Command'),s,(80,));self.assertFalse(clip.get('entryCard0').get('_visible'));self.assertEqual([],vm.errors)
 def test_controller_tabs_and_pages_stay_in_bounds(self):
  vm,s,calls=self.open();vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(1,s.get('tab'));self.assertEqual([],s.get('monthMoves'));self.assertEqual([],s.get('monthHires'));vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(2,s.get('tab'));vm.invoke(s.get('Command'),s,(51,));self.assertEqual(1,s.get('page'));vm.invoke(s.get('Command'),s,(50,));self.assertEqual(0,s.get('page'));vm.invoke(s.get('LocalEventHandler'),s,(12,None));self.assertEqual(0,s.get('tab'))
 def test_movements_share_month_but_have_independent_pages_and_profiles(self):
  model=copy.deepcopy(self.model);model['months']=[[202512,'Dezembro 2025'],[202601,'Janeiro 2026'],[202602,'Fevereiro 2026']];model['initialMonth']=2
  r=model['clubRows'][0];model['moveRows']=[[*r,20260115,'15/01/2026']];model['hireRows']=[[*r,20260116,'16/01/2026'] for _ in range(5)]+[[*r,20260203,'03/02/2026']]
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=Path(self.tmp.name)/'movements.big';native_screen.build(GAME,path,scenes_for(model,assets),assets,script_factory=script_factory(model,assets),full_name=FULL)
  vm,s,_,_=open_native(path,full=FULL);load_data(vm,s);vm.invoke(s.get('Command'),s,(1,));self.assertEqual(1,len(s.get('monthHires')));self.assertEqual(0,len(s.get('monthMoves')))
  vm.invoke(s.get('Command'),s,(30,));self.assertEqual(5,len(s.get('monthHires')));self.assertEqual(1,len(s.get('monthMoves')));self.assertEqual(2,s.get('hirePageCount'));vm.invoke(s.get('Command'),s,(53,));self.assertEqual(1,s.get('hirePage'));self.assertEqual(0,s.get('movePage'))
  vm.invoke(s.get('Command'),s,(44,));self.assertTrue(s.get('profile'));self.assertEqual(r[7],s.get('person'));vm.invoke(s.get('Command'),s,(60,));vm.invoke(s.get('Command'),s,(30,));self.assertEqual([],s.get('monthHires'));self.assertEqual([],s.get('monthMoves'));self.assertEqual(0,s.get('hirePage'));vm.invoke(s.get('Command'),s,(32,));self.assertEqual(0,s.get('month'));self.assertEqual([],vm.errors)
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
