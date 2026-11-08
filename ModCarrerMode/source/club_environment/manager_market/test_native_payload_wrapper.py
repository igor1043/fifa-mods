from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from PIL import Image
import test_screen
from test_lazy_profile import LazyProfileTest
from formats import AptFile,BigFile,Placement
from native_review_vm import open_native
from apt_vm import Object
from layout import Scene
from live_payload import build
from screen import profile_payload
from profile_media import describe

class NativeWrapperTests(unittest.TestCase):
 def child(self,fixture,person):
  scene=Scene('selected','');scene.image(person['head'],112,218,160,160);scene.nodes[-1]['name']='img_'+person['head']
  path=fixture.root/'wrapped.big';payload=dict(kind='profile',token='a'*64,person=0,date=20260120,encoded=profile_payload(person),artwork=describe(person))
  with patch('profile_media.prepare',return_value=(scene.pack(),{person['head']:Image.new('RGBA',(32,32),'red')})):build(test_screen.GAME,path,payload)
  child_vm,screen,apt,calls=open_native(path,full='game.screens.career.server16.ManagerLiveData')
  placement=next(p for p in apt.root_frames[0] if isinstance(p,Placement));self.assertEqual('Screen',placement.name);self.assertEqual(9,placement.character)
  outer=Object({placement.name:screen});screen.set('_parent',outer)
  return child_vm,screen,outer,calls
 def test_actual_outer_timeline_delivers_profile_and_selected_art(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   model=fixture.light();rich=fixture.light(model['people'][0]['id'])['people'][0]
   vm,state,calls=fixture.open(model);state.set('profile',True);state.set('person',0);state.set('profileLoaded',[])
   child_vm,screen,outer,_=self.child(fixture,rich);holder=Object(dict(content=outer,_visible=False));state.set('profileHolder',holder);state.get('scene1').set('profilePayload',holder)
   self.assertIsNone(outer.get('payloadReady'));self.assertTrue(screen.get('payloadReady'))
   before=len(calls);vm.invoke(state.get('profilePoll'),state)
   self.assertTrue(state.get('profileLoaded')[0]);self.assertTrue(state.get('scene1').get('_visible'))
   self.assertTrue(screen.get('scene0').get('img_'+rich['head']).get('_visible'));self.assertFalse(vm.errors)
   self.assertFalse(any(n in ('Initialize','BeginAnimateIn','SendEvent','unloadMovie') for n,a in calls[before:]))
   receipts=[args[-1] for name,args in calls[before:] if name=='SendSystemEvent' and 'Server16ManagerProfile' in args and args[-1].split('|')[2]=='-1']
   self.assertEqual(1,len(receipts));self.assertEqual('-1',receipts[0].split('|')[2])
   from profile_request import read
   received=read(fixture.request_file(receipts[0]),fixture.observed(),model,1100)
   self.assertIsNone(received['coach']);self.assertEqual(0,received['resume']['focus'])
  finally:fixture.tearDown()
 def test_currently_mounted_legacy_consumer_receives_deferred_parent_alias(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   person=fixture.light('1')['people'][0];vm,screen,outer,calls=self.child(fixture,person)
   inner=screen.get('scene0');screen.set('scene0',None)
   vm.invoke(screen.get('onEnterFrame'),screen);self.assertIsNone(outer.get('payloadReady'));self.assertIsNotNone(screen.get('onEnterFrame'))
   screen.set('scene0',inner);vm.invoke(screen.get('onEnterFrame'),screen)
   self.assertTrue(outer.get('payloadReady'));self.assertIs(inner,outer.get('scene0'));self.assertIs(screen.get('payload'),outer.get('payload'));self.assertIsNone(screen.get('onEnterFrame'))
   self.assertFalse(vm.errors);self.assertFalse(any(n in ('SetLocalEventHandler','Initialize','SendEvent') for n,a in calls))
  finally:fixture.tearDown()
 def test_history_transport_also_resolves_native_screen_wrapper(self):
  fixture=test_screen.NativeScreenTest;fixture.setUpClass()
  try:
   vm,state,calls=fixture().open();state.set('historyPending',True);state.set('clubTimeline',True);state.set('requestedHistoryClub',1)
   payload=Object(dict(kind='history',token=fixture.model.get('profileToken',''),club=1,date=fixture.model['date'],data=Object(dict(club=1,name='Clube',crest='crest_1',rows=[]))))
   state.set('historyHolder',Object(dict(content=Object(dict(Screen=Object(dict(payloadReady=True,payload=payload)))))))
   vm.invoke(state.get('historyPoll'),state);self.assertFalse(state.get('historyPending'));self.assertTrue(state.get('scene7').get('_visible'));self.assertFalse(vm.errors)
  finally:fixture.tearDownClass()

 def test_receiver_is_active_outside_the_hidden_profile_during_first_load(self):
  fixture=LazyProfileTest();fixture.setUp()
  try:
   vm,state,calls=fixture.open(fixture.light());state.set('profile',True);state.set('person',0);state.set('profileLoaded',[])
   holder=Object(dict(content=Object(),_visible=True,_alpha=0));parent=state.get('scene1');parent.set('_visible',False)
   state.set('profileHolder',holder);vm.invoke(state.get('profilePoll'),state)
   self.assertIs(holder,parent.get('profilePayload'));self.assertTrue(holder.get('_visible'));self.assertEqual(0,holder.get('_alpha'))
   self.assertFalse(parent.get('_visible'));self.assertFalse(vm.errors)
  finally:fixture.tearDown()
