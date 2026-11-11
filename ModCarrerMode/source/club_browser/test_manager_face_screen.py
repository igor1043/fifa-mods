"""Run the actual appended AVM code, preserving native preference behavior."""
from pathlib import Path
import os,tempfile,unittest
import build_manager_face as screen
from formats import BigFile,AptFile
from apt_actions import Actions
from apt_vm import Object,Native
from apt_test_vm import NativeVM

class FaceVM(NativeVM):
 def get(self,obj,key):
  if isinstance(obj,list) and key=='splice':return Native('splice')
  return super().get(obj,key)
 def invoke(self,function,owner,args=()):
  if self.depth==0:self.steps=0
  if isinstance(function,Native) and function.name=='splice':
   at,count=int(args[0]),int(args[1]);removed=owner[at:at+count];owner[at:at+count]=args[2:];return removed
  return super().invoke(function,owner,args)

class Screen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();folder=Path(cls.temp.name)
  original=Path(os.environ['MANAGER_FACE_ORIGINAL']);cls.out=folder/'screen.big'
  cls.report=screen.build(Path(os.environ['SERVER16_GAME_ROOT']),original,cls.out,folder/'catalog.tsv')
  before=AptFile(BigFile(original));after=AptFile(BigFile(cls.out));cls.apt=after
  cls.assert_native_exports=(before.exports==after.exports)
  registration=lambda apt:next(c for c in apt.root_frames[0] if isinstance(c,tuple) and c[0]=='init' and c[1]==apt.exports[screen.b.FULL])
  old=Actions(before).read_all().cache[registration(before)[-1]]
  new=Actions(after).read_all().cache[registration(after)[-1]]
  cls.code=new[len(old)-1:]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def setUp(self):
  self.calls=[];self.rows=[Object(dict(NAME='CONTINUE',TYPE=7))]+[Object(dict(NAME=name,TYPE=0)) for name in ('firstname','surname','nationality','clothing','color','skin','body')]
  def callback(name,owner,args):
   self.calls.append((name,args))
   if name=='baseInit':owner.set('m_RowData',self.rows.copy())
   if name=='baseInput':return 'native-result'
   if name=='baseHelp':return ['native-help']
   if name in ('CreateHelpTickerItem','Create'):return tuple(args)
   if name=='getSelectedIndex':return self.index
   if name=='localToGlobal':
    point=args[0];point.set('x',(point.get('x')+145)*self.root_scale+self.root_offset);point.set('y',(point.get('y')+440)*self.root_scale)
   if name=='globalToLocal':
    point=args[0];point.set('x',(point.get('x')-self.root_offset)/self.root_scale);point.set('y',point.get('y')/self.root_scale)
  self.vm=FaceVM(callback);proto=Object({method:Native(name) for method,name in [('_InitComponentsData','baseInit'),('_LocalEventHandler','baseInput'),('getHelpContext','baseHelp'),('_OnExitScreen','baseExit'),('_OnAnimateInComplete','baseComplete'),('_UpdateRow','baseUpdateRow')]})
  self.klass=Object(dict(prototype=proto,TYPE_BUTTON=7))
  help=Object({k:Native(k) for k in ('Update','Show','SetCustomSource')})
  self.vm.global_.set('game',Object(dict(screens=Object(dict(career=Object(dict(ManagerPreferences=self.klass)))),globalClasses=Object(dict(HelpManager=help)))))
  self.codes=dict(BACK=1,ADVANCE=2,UI_UP=3,UI_DOWN=4,PAGE_UP=5,PAGE_DOWN=6,OPTION_TOP=7,START=8,MENU=9,PAUSE=10)
  self.vm.global_.set('INPUTCODE',Object(self.codes));self.vm.global_.set('ION_CareerMode',Object(dict(SendSystemEvent=Native('SendSystemEvent'))))
  self.vm.global_.set('cafe',Object(dict(utility=Object(dict(Delegate=Object(dict(Create=Native('Create'))))))))
  self.vm.global_.set('ion',Object(dict(manager=Object(dict(HelpItem=Object(dict(CreateHelpTickerItem=Native('CreateHelpTickerItem'))))))))
  self.vm.global_.set('Mouse',Object(dict(addListener=Native('addListener'),removeListener=Native('removeListener'))))
  self.vm.run(self.code,self.vm.global_,self.vm.global_)
  clips={name:Object(dict(_visible=name!='mcImageLoader')) for name in screen.NATIVE_CLIPS}
  clips['mcRowControl'].set('getSelectedIndex',Native('getSelectedIndex'))
  clips['mcMainFrame'].set('_width',990)
  self.root_scale=1.5;self.root_offset=0
  self.view=Object(dict(clips,m_StaticData=Object(dict(SCREEN_CONTROLLER_ID='ManagerPrefs')),globalToLocal=Native('globalToLocal')),proto)
  self.index=0;self.invoke('_InitComponentsData')
 def invoke(self,name,*args):return self.vm.invoke(self.view.get(name),self.view,args)
 def press(self,key):return self.invoke('_LocalEventHandler',self.codes[key],True)
 def commands(self):return [args[-1] for name,args in self.calls if name=='SendSystemEvent']
 def test_native_fields_and_input_preserved_and_face_follows_nationality(self):
  self.assertTrue(self.assert_native_exports);self.assertGreater(self.report['faces'],0)
  rows=self.view.get('m_RowData');self.assertEqual(len(rows),9)
  self.assertEqual([row for row in rows if not row.get('S16Face')],self.rows)
  self.assertTrue(rows[4].get('S16Face'));self.assertEqual(rows[4].get('LABEL'),'Face')
  self.assertEqual(rows[4].get('NAME'),rows[0].get('NAME'));self.assertEqual(rows[3].get('NAME'),'nationality')
  self.assertEqual(self.press('ADVANCE'),'native-result');self.assertEqual(self.invoke('getHelpContext'),['native-help'])
  self.assertEqual(sum(name=='baseInput' for name,args in self.calls),1)
 def test_confirm_cancel_and_native_initialization_are_separate(self):
  self.index=4;self.press('ADVANCE');self.assertEqual(self.commands(),['open']);self.assertFalse(self.view.get('mcMainFrame').get('_visible'))
  self.assertTrue(all(not self.view.get(name).get('_visible') for name in screen.NATIVE_CLIPS))
  self.press('UI_DOWN');self.assertEqual(self.commands()[-1],'down')
  self.assertEqual([x[0] for x in self.invoke('getHelpContext')],['ADVANCE','BACK','LAS_UD','RAS_LR','L1R1','OPTION_TOP'])
  self.press('BACK');self.assertEqual(self.commands()[-1],'cancel');self.assertTrue(self.view.get('mcMainFrame').get('_visible'))
  self.assertFalse(self.view.get('mcImageLoader').get('_visible'));self.assertTrue(self.view.get('mcRowControl').get('_visible'))
  self.press('ADVANCE');self.press('START');self.assertEqual(self.commands()[-1],'confirm')
  self.index=0;self.press('ADVANCE');self.assertEqual(self.commands()[-1],'arm');self.invoke('_OnExitScreen');self.assertEqual(self.commands()[-2:],['arm','row_hide'])
 def test_mouse_confirm_and_keyboard_back_without_the_removed_back_hotspot(self):
  self.index=4;self.press('ADVANCE');self.view.set('_xmouse',100);self.view.set('_ymouse',620);self.invoke('onMouseDown');self.assertEqual(self.commands()[-1],'confirm')
  self.press('ADVANCE');self.view.set('_xmouse',450);self.view.set('_ymouse',50);self.invoke('onMouseDown');self.assertTrue(self.view.get('S16FaceActive'));self.assertEqual(self.commands()[-1],'open')
  self.press('BACK');self.assertEqual(self.commands()[-1],'cancel')
  self.assertFalse(any(name=='baseInput' for name,args in self.calls))
 def test_background_updates_on_ui_owner_and_original_frame_is_restored(self):
  original=Native('priorFrame');self.view.set('onEnterFrame',original)
  self.invoke('_OnAnimateInComplete')
  self.assertEqual(self.view.get('onEnterFrame'),self.view.get('S16FaceFrame'))
  for _ in range(7):self.invoke('S16FaceFrame')
  ticks=[args for name,args in self.calls if name=='SendSystemEvent' and args[-2]=='Server16FrontendTick']
  self.assertEqual([tuple(tick) for tick in ticks],[('Calendar','Server16FrontendTick','tick')]*2)
  self.assertEqual(sum(name=='priorFrame' for name,args in self.calls),7)
  self.invoke('_OnExitScreen');self.assertEqual(self.view.get('onEnterFrame'),original)
 def test_reentering_preferences_does_not_wrap_its_own_override(self):
  prior=self.view.get('S16BaseInit');handler=self.view.get('_InitComponentsData')
  self.vm.run(self.code,self.vm.global_,self.vm.global_)
  self.assertIs(self.view.get('S16BaseInit'),prior);self.assertIs(self.view.get('_InitComponentsData'),handler)
  self.invoke('_InitComponentsData');self.assertEqual(len(self.view.get('m_RowData')),9)
 def test_native_row_publishes_its_value_position_and_preserves_other_rows(self):
  row=Object(dict(txtLink=Object(dict(_visible=True,_x=495,_y=0,_width=76,_height=29)),mcInputText=Object(dict(_x=493)),txtButton=Object(dict(_y=0,_height=29)),localToGlobal=Native('localToGlobal')))
  self.invoke('_UpdateRow',row,4);self.assertIs(self.view.get('S16FaceValueRow'),row);self.assertFalse(row.get('txtLink').get('_visible'))
  self.index=4;self.invoke('S16FacePublishValue');self.assertEqual(self.commands()[-2:],['row:638,440,465,29','row_focus'])
  before=len(self.commands())
  for _ in range(60):self.invoke('S16FacePublishValue')
  self.assertEqual(len(self.commands()),before,'Stationary preferences must not flood native commands')
  self.root_scale=2;self.root_offset=420
  self.invoke('S16FacePublishValue');self.assertEqual(len(self.commands()),before,'Ultrawide/root scale must not displace the value')
  self.index=3;self.invoke('S16FacePublishValue');self.assertEqual(self.commands()[-1],'row_blur')
  other=Object(dict(txtLink=Object(dict(_visible=True))));self.invoke('_UpdateRow',other,2)
  self.assertTrue(other.get('txtLink').get('_visible'));self.assertIs(self.view.get('S16FaceValueRow'),row)
  self.assertEqual(sum(name=='baseUpdateRow' for name,args in self.calls),2)
  self.index=4;self.press('ADVANCE');before=len(self.commands());self.invoke('S16FacePublishValue');self.assertEqual(len(self.commands()),before)
  self.press('BACK');self.assertEqual(self.commands()[-2:],['row:638,440,465,29','row_focus'])
  self.invoke('_OnExitScreen');self.assertIn('row_hide',self.commands())
 def test_face_scope_notifies_the_actual_background_on_open_and_close(self):
  owner=Object(dict(S16SyncManagerFaceBackground=Native('syncBackground')))
  self.vm.global_.set('Server16ManagerFaceBackgroundOwner',owner)
  self.vm.global_.set('Server16ManagerFaceBootBackgroundOwner',Object(dict(S16SyncManagerFaceBackground=Native('syncBootBackground'))))
  self.index=4;self.press('ADVANCE');self.assertTrue(self.vm.global_.get('Server16ManagerFaceActive'))
  for _ in range(60):self.invoke('S16FaceFrame')
  self.press('BACK');self.assertFalse(self.vm.global_.get('Server16ManagerFaceActive'))
  self.assertEqual(sum(name=='syncBackground' for name,args in self.calls),2)
  self.assertEqual(sum(name=='syncBootBackground' for name,args in self.calls),2)
 def test_original_fifa_class_and_native_rows_receive_the_extension(self):
  apt=self.apt;actions=Actions(apt).read_all()
  definition=next(row for row in apt.root_frames[0] if isinstance(row,tuple) and row[:2]==('init',19))
  registration=next(row for row in apt.root_frames[0] if isinstance(row,tuple) and row[:2]==('init',18))
  native_rows=[Object(dict(NAME='Continue',TYPE='BUTTON'))]+[Object(dict(NAME=name,TYPE='INPUT')) for name in ('FirstName','Surname','Nationality','Clothes','Color','Skin','Body')]
  vm=FaceVM(lambda name,owner,args:native_rows if name=='GetScreenComponentData' else None)
  base=Object(dict(prototype=Object()))
  vm.global_.set('ion',Object(dict(screen=Object(dict(BaseScreen=base)))))
  vm.global_.set('ION_CareerMode',Object(dict(GetScreenComponentData=Native('GetScreenComponentData'))))
  vm.run(actions.cache[definition[-1]],vm.global_,vm.global_)
  vm.run(actions.cache[registration[-1]],vm.global_,vm.global_)
  klass=vm.path('game.screens.career.ManagerPreferences')
  view=Object(dict(m_ScreenComponents=[Object(dict(NAME='RowData'))]),klass.get('prototype'))
  vm.invoke(view.get('_InitComponentsData'),view)
  rows=view.get('m_RowData')
  self.assertEqual(len(rows),9);self.assertEqual(rows[4].get('LABEL'),'Face')
  self.assertEqual(rows[4].get('TYPE'),klass.get('TYPE_BUTTON'))
  self.assertEqual(rows[4].get('NAME'),'Continue')
  self.assertEqual([r for r in rows if not r.get('S16Face')],[native_rows[i] for i in (0,1,2,3,5,6,7,8)])

if __name__=='__main__':unittest.main()
