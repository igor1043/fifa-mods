import tempfile,unittest
from pathlib import Path
import build_loading as loading
from formats import BigFile,AptFile,Placement
from apt_actions import Actions
from apt_test_vm import NativeVM
from apt_vm import Object,Native

class PreviewLoadingTests(unittest.TestCase):
 def test_native_waiting_view_has_no_old_fixture_and_back_uses_calendar_controller(self):
  with tempfile.TemporaryDirectory() as folder:
   apt=AptFile(BigFile(loading.build(Path(folder)/'waiting.big')))
  actions=Actions(apt).read_all();self.assertFalse(actions.errors)
  calls=[]
  def native(name,obj,args):
   calls.append((name,args))
   if name=='Create':return tuple(args)
   if name=='GetScreenStaticData':return Object({'SCREEN_CONTROLLER_ID':'Calendar'})
   if name=='GetEvents':return Object({'BACK':'Back'})
  vm=NativeVM(native)
  managers={k:Object({n:Native(n) for n in ns}) for k,ns in {'ScreenManager':['SetOnExitScreenCallback','BeginAnimateIn'],'InputManager':['SetLocalEventHandler','DisableCurrentLocalEventHandler'],'HelpManager':['Update','Clear']}.items()}
  managers['InputCodes']=Object({'BACK':1})
  vm.global_.set('game',Object({'globalClasses':Object(managers)}))
  vm.global_.set('ION_CareerMode',Object({n:Native(n) for n in ('GetScreenStaticData','GetEvents','SendEvent','SendSystemEvent')}))
  vm.global_.set('cafe',Object({'utility':Object({'Delegate':Object({'Create':Native('Create')})})}))
  vm.global_.set('ion',Object({'screen':Object({'BaseScreen':Object({'prototype':Object({'Initialize':Native('Initialize'),'Shutdown':Native('Shutdown')})})}),'manager':Object({'HelpItem':Object({'CreateHelpTickerItem':Native('CreateHelpTickerItem')})})}))
  full='.'.join(loading.CLASS);blocks=list(actions.cache.values());vm.pending_packages={full:blocks[0]}
  vm.run(blocks[1],vm.global_,vm.global_);klass=vm.path(full)
  screen=Object({p.name:Object() for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name},klass.get('prototype'))
  vm.invoke(klass,screen)
  self.assertTrue(any(name=='BeginAnimateIn' for name,args in calls))
  self.assertIn('Atualizando',screen.get('message').get('text'))
  self.assertEqual(screen.get('status').get('text'),'')
  self.assertIsNone(screen.get('userPitch'));self.assertIsNone(screen.get('opponentPitch'))
  vm.invoke(screen.get('LocalEventHandler'),screen,[1,None])
  self.assertIn(('SendEvent',['Calendar','Back','']),calls)
  vm.invoke(screen.get('OnExitScreen'),screen);self.assertIsNone(screen.get('onEnterFrame'))

if __name__=='__main__':unittest.main()
