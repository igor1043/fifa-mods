import json,tempfile,unittest,zipfile,io
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import test_screen
from test_lazy_profile import LazyProfileTest
from profile_layout import profile_scene
from profile_media import subset,describe
from live_payload import build,publish,cleanup_profile_media
from native_review_vm import open_native
from apt_vm import Object
from screen import profile_payload
from layout import Scene

class SelectedMediaTests(unittest.TestCase):
 def test_profile_geometry_does_not_grow_with_global_catalogue(self):
  pixel=Image.new('RGBA',(1,1));assets={**{'head_'+str(i):pixel for i in range(2000)},**{'crest_'+str(i):pixel for i in range(1700)}}
  before=profile_scene(dict(assets));after=profile_scene(dict(assets),external_art=True)
  self.assertGreater(len(before.nodes),8000);self.assertLess(len(after.nodes),400)
  self.assertFalse(any(n.get('asset','').startswith(('head_','crest_','competition_','flag_')) for n in after.nodes))
 def test_subset_decodes_only_selected_images(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'ModCarrerMode/runtime/manager_market/artwork_cache/art_test.zip';path.parent.mkdir(parents=True)
   data=io.BytesIO();Image.new('RGBA',(32,32),'red').save(data,format='PNG')
   with zipfile.ZipFile(path,'w') as z:z.writestr('index.json',json.dumps(['head_one','head_unrelated']));z.writestr('0.png',data.getvalue());z.writestr('1.png',b'not an image')
   selected=subset(folder,{'head_one'},'test');self.assertEqual({'head_one'},set(selected));self.assertEqual((32,32),selected['head_one'].size)
 def test_native_selected_art_stays_mounted_after_profile_arrives(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   base=fixture.light();rich=fixture.light('1');person=next(i for i,p in enumerate(rich['people']) if p['id']=='1');data=rich['people'][person]
   vm,state,calls=fixture.open(base);state.set('profile',True);state.set('person',person);state.set('profileLoaded',[])
   scene=Scene('selected','');scene.image(data['head'],112,218,160,160);scene.nodes[-1]['name']='img_'+data['head']
   target=fixture.root/'media.big';payload=dict(kind='profile',token=base['profileToken'],person=person,date=base['date'],encoded=profile_payload(data),artwork=describe(data))
   with patch('profile_media.prepare',return_value=(scene.pack(),{data['head']:Image.new('RGBA',(32,32),'red')})):build(test_screen.GAME,target,payload)
   child_vm,child,_,_=open_native(target,full='game.screens.career.server16.ManagerLiveData')
   art=child.get('scene0').get('img_'+data['head']);art.set('_visible',True);self.assertTrue(child.get('payloadReady'))
   holder=Object(dict(content=child,_visible=False));state.set('profileHolder',holder);state.get('scene1').set('profilePayload',holder)
   mounted=child.get('scene0');child.set('scene0',Object());start=len(calls)
   vm.invoke(state.get('profilePoll'),state)
   self.assertFalse(state.get('profileLoaded'));self.assertFalse(holder.get('_visible'))
   self.assertFalse(any(name=='unloadMovie' for name,args in calls[start:]))
   child.set('scene0',mounted);vm.invoke(state.get('profilePoll'),state)
   self.assertTrue(state.get('profileLoaded')[person]);self.assertTrue(art.get('_visible'));self.assertTrue(holder.get('_visible'))
   self.assertFalse(any(name in ('unloadMovie','Initialize','BeginAnimateIn','SendEvent') for name,args in calls[start:]))
   vm.invoke(state.get('Command'),state,[60]);self.assertFalse(state.get('scene1').get('_visible'));self.assertFalse(vm.errors)
  finally:fixture.tearDown()
 def test_loading_child_is_not_cancelled_each_poll(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   vm,state,calls=fixture.open(fixture.light());state.set('profileHolder',Object(dict(content=Object())));state.set('profileLoading',True);state.set('profileLoadFrames',0)
   start=len(calls)
   for _ in range(15):vm.invoke(state.get('profilePoll'),state)
   self.assertEqual(15,state.get('profileLoadFrames'));self.assertFalse(any(n in ('loadMovie','unloadMovie') for n,a in calls[start:]));self.assertFalse(vm.errors)
  finally:fixture.tearDown()
 def test_profile_files_are_scoped_and_cleanup_leaves_other_assets(self):
  with tempfile.TemporaryDirectory() as folder:
   game=Path(folder);root=game/'runtime';root.mkdir()
   def packet(game,path,data):Path(path).write_bytes(data['token'].encode())
   with patch('live_payload.build',side_effect=packet):
    for token,person in (('a'*64,1),('a'*64,2),('b'*64,1)):publish(game,root,'managerprofile',dict(kind='profile',token=token,person=person,artwork={'selected':True}))
   files=list((game/'data/ui/game/screens/career/server16').glob('*.big'));self.assertEqual(6,len(files))
   other=files[0].parent/'managerprofile0.big';other.write_bytes(b'legacy asset');self.assertEqual(6,cleanup_profile_media(game));self.assertTrue(other.is_file())

 def test_focus_prefetches_once_without_opening_profile_or_mutating_input(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   vm,state,calls=fixture.open(fixture.light());state.set('focus',40);start=len(calls)
   for _ in range(12):vm.invoke(state.get('ScrollFrame'),state)
   requests=[a for n,a in calls[start:] if n=='SendSystemEvent' and 'Server16ManagerProfile' in a]
   self.assertEqual(1,len(requests));self.assertFalse(state.get('profile'));self.assertEqual(40,state.get('focus'));self.assertFalse(vm.errors)
  finally:fixture.tearDown()

 def test_cached_cv_still_polls_for_its_own_art_after_another_coach(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   vm,state,calls=fixture.open(fixture.light());state.set('profile',True);state.set('person',0);state.set('profileLoaded',[True]);state.set('profileMediaPerson',1)
   state.set('profileHolder',Object(dict(content=Object())));state.set('profileLoading',True);state.set('profileLoadFrames',0)
   vm.invoke(state.get('ScrollFrame'),state);self.assertEqual(1,state.get('profileLoadFrames'));self.assertFalse(vm.errors)
  finally:fixture.tearDown()

