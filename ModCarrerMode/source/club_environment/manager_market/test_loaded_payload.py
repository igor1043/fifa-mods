from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from PIL import Image
import test_screen
from live_payload import build
from formats import AptFile,BigFile
from apt_actions import Actions
from apt_vm import Object
from native_review_vm import MarketVM
from layout import Scene

class EmbeddedPayloadTests(unittest.TestCase):
 def timeline(self,path):
  apt=AptFile(BigFile(path));actions=Actions(apt).read_all();self.assertFalse(actions.errors)
  calls=[];vm=MarketVM(lambda name,owner,args:calls.append(name));clip=Object()
  # A loadMovie child receives frame actions, not ScreenManager's constructor.
  vm.run(list(actions.cache.values())[0],clip,clip)
  self.assertFalse(vm.errors);return clip,calls
 def test_load_movie_timeline_delivers_without_instantiating_screen_class(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'data.big';build(test_screen.GAME,path,dict(kind='profile',person=7,date=20260302,token='career',encoded='selected coach'))
   clip,calls=self.timeline(path)
   self.assertTrue(clip.get('payloadReady'));self.assertEqual('selected coach',clip.get('payload').get('encoded'))
   self.assertFalse(any(name in ('Initialize','SetLocalEventHandler','SendEvent','BeginAnimateIn') for name in calls))
 def test_embedded_artwork_names_are_ready_without_class_constructor(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'art.big';s=Scene('selected','');s.image('head_selected',112,218,160,160);s.nodes[-1]['name']='selectedPortrait'
   with patch('profile_media.prepare',return_value=(s.pack(),{'head_selected':Image.new('RGBA',(32,32),'red')})):build(test_screen.GAME,path,dict(kind='profile',artwork={'selected':True},person=7))
   clip,_=self.timeline(path);self.assertTrue(clip.get('payloadReady'));self.assertEqual(['selectedPortrait'],clip.get('payload').get('artworkNames'))
 def test_history_rows_also_arrive_from_frame_actions(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'history.big';build(test_screen.GAME,path,dict(kind='history',data=dict(rows=[['Coach 1',20],['Coach 2',32]])))
   clip,_=self.timeline(path);self.assertEqual(2,len(clip.get('payload').get('data').get('rows')))
