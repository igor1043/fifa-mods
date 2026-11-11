from pathlib import Path
import os,tempfile,unittest
import build_manager_face_background as builder
from formats import AptFile,BigFile
from apt_actions import Actions
from apt_vm import Object,Native
from apt_test_vm import NativeVM

class Background(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.output=Path(cls.temp.name)/'background.big'
  source=Path(os.environ['MANAGER_FACE_BACKGROUND_ORIGINAL'])
  builder.build(source,cls.output)
  old=AptFile(BigFile(source));new=AptFile(BigFile(cls.output));old_actions=Actions(old).read_all();new_actions=Actions(new).read_all()
  init=lambda apt:next(row for row in apt.root_frames[0] if isinstance(row,tuple) and row[:2]==('init',2))
  cls.code=new_actions.cache[init(new)[-1]][len(old_actions.cache[init(old)[-1]])-1:]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def setUp(self):
  self.calls=[]
  def call(name,owner,args):
   self.calls.append((name,args))
   if name=='nativeComplete':owner.set('_visible',True)
   if name=='nativeLoad':return bool(args and args[0])
  self.vm=NativeVM(call);self.proto=Object(dict(LoadImage=Native('nativeLoad'),LoadImageComplete=Native('nativeComplete')))
  self.vm.global_.set('game',Object(dict(background=Object(dict(BackgroundFIFA=Object(dict(prototype=self.proto)))))))
  self.vm.run(self.code,self.vm.global_,self.vm.global_)
  self.view=Object(dict(_visible=True),self.proto)
 def invoke(self,name,*args):return self.vm.invoke(self.view.get(name),self.view,args)
 def test_native_load_callbacks_and_menu_visibility_are_preserved(self):
  marker=Object();self.assertTrue(self.invoke('LoadImage','BOOTFLOW'));self.assertFalse(self.invoke('LoadImage',''));self.calls.clear()
  self.invoke('LoadImage','BOOTFLOW');self.invoke('LoadImageComplete',marker)
  self.assertTrue(self.view.get('_visible'));self.assertEqual(self.calls,[('nativeLoad',['BOOTFLOW']),('nativeComplete',[marker])])
  self.assertIs(self.vm.global_.get(builder.OWNER),self.view)
 def test_face_hides_actual_photograph_and_close_restores_it(self):
  self.invoke('LoadImage','BOOTFLOW');self.vm.global_.set(builder.ACTIVE,True);self.invoke(builder.SYNC)
  self.assertFalse(self.view.get('_visible'));self.assertTrue(self.view.get('S16FaceHidden'))
  self.invoke('LoadImageComplete',Object());self.assertFalse(self.view.get('_visible'))
  self.vm.global_.set(builder.ACTIVE,False);self.invoke(builder.SYNC)
  self.assertTrue(self.view.get('_visible'));self.assertFalse(self.view.get('S16FaceHidden'))
  self.view.set('_visible',False);self.invoke(builder.SYNC);self.assertFalse(self.view.get('_visible'))
 def test_missing_face_mode_does_not_force_hidden_background_visible(self):
  self.view.set('_visible',False);self.invoke('LoadImage','BOOTFLOW');self.assertFalse(self.view.get('_visible'))
 def test_reloaded_background_does_not_wrap_its_own_callbacks(self):
  original=self.view.get('S16FaceNativeLoadImage');method=self.view.get('LoadImage')
  self.vm.run(self.code,self.vm.global_,self.vm.global_)
  self.assertIs(self.view.get('S16FaceNativeLoadImage'),original);self.assertIs(self.view.get('LoadImage'),method)

class BootBackground(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.output=Path(cls.temp.name)/'boot.big'
  source=Path(os.environ['MANAGER_FACE_BOOT_BACKGROUND_ORIGINAL'])
  builder.build(source,cls.output)
  old=AptFile(BigFile(source));new=AptFile(BigFile(cls.output))
  init=lambda apt:next(row for row in apt.root_frames[0] if isinstance(row,tuple) and row[:2]==('init',2))
  old_code=Actions(old).read_all().cache[init(old)[-1]];new_code=Actions(new).read_all().cache[init(new)[-1]]
  cls.code=new_code[len(old_code)-1:]
  cls.exports_preserved=old.exports==new.exports
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_creation_bootflow_owns_its_image_without_replacing_stadium_owner(self):
  calls=[];vm=NativeVM(lambda name,owner,args:calls.append((name,args)))
  proto=Object(dict(LoadImageComplete=Native('bootComplete')))
  vm.global_.set('game',Object(dict(background=Object(dict(BackgroundBootflow=Object(dict(prototype=proto)))))))
  stadium=Object();vm.global_.set(builder.OWNER,stadium)
  vm.run(self.code,vm.global_,vm.global_);image=Object(dict(_visible=True));view=Object(dict(_visible=True,mcImageLoader=image),proto)
  vm.invoke(view.get('LoadImageComplete'),view,[Object()])
  self.assertTrue(self.exports_preserved);self.assertEqual(calls[0][0],'bootComplete')
  self.assertIs(vm.global_.get(builder.BOOT_OWNER),view);self.assertIs(vm.global_.get(builder.OWNER),stadium)
  self.assertTrue(view.get('_visible'))
  vm.global_.set(builder.ACTIVE,True);vm.invoke(view.get(builder.SYNC),view)
  self.assertFalse(view.get('_visible'))
  self.assertFalse(image.get('_visible'))
  # A late cached image completion must not expose the opening photograph.
  view.set('_visible',True);vm.invoke(view.get('LoadImageComplete'),view)
  self.assertFalse(view.get('_visible'))
  vm.global_.set(builder.ACTIVE,False);vm.invoke(view.get(builder.SYNC),view)
  self.assertTrue(view.get('_visible'))
  self.assertTrue(image.get('_visible'))

if __name__=='__main__':unittest.main()
