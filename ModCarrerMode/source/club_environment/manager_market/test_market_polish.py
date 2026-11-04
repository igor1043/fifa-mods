"""Regressions for mixed mouse/controller market navigation and real exit events."""
import copy,tempfile,unittest
from pathlib import Path
import test_screen as screen_test
from test_screen import load_data,GAME,scenes_for,script_factory,FULL,stars,native_screen,open_native,Image,Object
import test_engine as engine_test

class MarketPolishTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  screen_test.NativeScreenTest.setUpClass();cls.tmp=tempfile.TemporaryDirectory();cls.model=copy.deepcopy(screen_test.NativeScreenTest.model)
  cls.model['months']=[[y*100+m,['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][m-1]] for y in (2025,2026) for m in range(1,13)];cls.model['initialMonth']=23
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  cls.package=Path(cls.tmp.name)/'polish.big';native_screen.build(GAME,cls.package,scenes_for(cls.model,assets),assets,script_factory=script_factory(cls.model,assets),full_name=FULL)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup();screen_test.NativeScreenTest.tearDownClass()
 def open(self,setup=None):
  vm,s,_,_=open_native(self.package,full=FULL,setup=setup);load_data(vm,s);return vm,s
 def click(self,vm,s,scene,code):
  boxes=scenes_for(self.model,{})[scene]['actions'];index=next(i for i,b in enumerate(boxes) if int(b['target'])==code);box=boxes[index];x=s.get('scene'+str(scene)).get('action'+str(index)).get('_x') if code in (51,53,55) else box['x'];s.set('_xmouse',x+box['w']/2);s.set('_ymouse',box['y']+box['h']/2);vm.invoke(s.get('onMouseDown'),s);vm.invoke(s.get('onMouseUp'),s)
 def test_arrows_and_dots_click_and_keyboard_use_the_same_page(self):
  vm,s=self.open();s.set('clubs',s.get('clubs')*8);vm.invoke(s.get('Refresh'),s)
  self.click(vm,s,0,51);self.assertEqual(1,s.get('page'));self.click(vm,s,0,50);self.assertEqual(0,s.get('page'))
  s.set('focus',51);s.set('mouseSelectFrames',0);vm.invoke(s.get('LocalEventHandler'),s,(2,None));self.assertEqual(1,s.get('page'))
  self.click(vm,s,0,102);self.assertEqual(2,s.get('page'));self.assertTrue(s.get('scene0').get('pageDotOn2').get('_visible'));self.assertEqual([],vm.errors)
 def test_current_club_defaults_year_dropdown_and_single_month_steps(self):
  vm,s=self.open();vm.invoke(s.get('Command'),s,(1,));self.assertEqual(self.model['initialCountry']+1,s.get('movementCountry'));self.assertEqual(self.model['initialLeague'],s.get('movementLeagueId'))
  self.assertEqual('Dezembro',s.get('scene3').get('monthName').get('text'));self.assertEqual(2026,s.get('scene3').get('yearName').get('text'))
  self.click(vm,s,3,38);self.assertTrue(s.get('yearMenu'));vm.invoke(s.get('Move'),s,(2,));self.assertEqual(300,s.get('focus'));s.set('mouseSelectFrames',0);vm.invoke(s.get('LocalEventHandler'),s,(2,None))
  self.assertFalse(s.get('yearMenu'));self.assertEqual(11,s.get('month'));self.assertEqual(2025,s.get('scene3').get('yearName').get('text'))
  vm.invoke(s.get('Command'),s,(31,));self.assertEqual(12,s.get('month'));self.assertEqual('Janeiro',s.get('scene3').get('monthName').get('text'));self.assertEqual(2026,s.get('scene3').get('yearName').get('text'));self.assertEqual([],vm.errors)
 def test_independent_list_arrows_dots_and_nonrenewal_status(self):
  vm,s=self.open();vm.invoke(s.get('Command'),s,(1,));country=s.get('countries')[s.get('movementCountry')-1][0];row=list(self.model['clubRows'][0])+[20261202,'02/12/2026',country];row[3]='Não renovou';s.set('moves',[row]*12);s.set('hires',[row]*9);vm.invoke(s.get('Refresh'),s)
  self.assertEqual('Não renovou',s.get('scene3').get('status4').get('text'));self.click(vm,s,3,53);self.assertEqual(1,s.get('hirePage'));self.assertEqual(0,s.get('movePage'))
  self.click(vm,s,3,142);self.assertEqual(8,s.get('movePage'));self.assertEqual(1,s.get('hirePage'));self.click(vm,s,3,54);self.assertEqual(7,s.get('movePage'));self.assertEqual([],vm.errors)
 def test_help_moves_and_restores_original_native_footer(self):
  holder=Object({'_y':940});scroller=Object({'_y':946})
  def setup(vm,calls):vm.path('game.globalClasses.HelpManager').set('mcHelpDisplay',Object({'mcHelpItemsHolder':holder,'mcTextScroller':scroller}))
  vm,s=self.open(setup);self.assertEqual(1030,holder.get('_y'));vm.invoke(s.get('OnExitScreen'),s);self.assertEqual(940,holder.get('_y'));self.assertEqual(946,scroller.get('_y'));self.assertEqual([],vm.errors)

class MovementStatusTest(unittest.TestCase):
 setUp=engine_test.EngineTest.setUp
 tearDown=engine_test.EngineTest.tearDown
 def test_nonrenewal_is_listed_as_exit_without_rewriting_dates(self):
  from model import project
  a=self.m.active(club=1);self.m.leave(a,20261202,'resignation','Treinador optou por não renovar ao término do contrato')
  data=project(self.m);row=next(r for r in data['moveRows'] if r[0]=='Clube 1');self.assertEqual('Não renovou',row[3]);self.assertEqual(20261202,row[9]);self.assertEqual(0,len(data['hireRows']))

if __name__=='__main__':unittest.main()
