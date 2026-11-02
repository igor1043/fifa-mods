from pathlib import Path
import copy,hashlib,json,tempfile,unittest
import test_screen
from test_screen import GAME,load_data
from PIL import Image
import screen,native_screen,template_renderer
from formats import BigFile,AptFile,chunk_unwrap
from apt_actions import Actions
from native_review_vm import open_native

class FastTemplateTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  test_screen.NativeScreenTest.setUpClass();cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name)
  cls.model=copy.deepcopy(test_screen.NativeScreenTest.model);cls.template=root/'catalogue.big'
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(256,256),'gray')}
  native_screen.build(GAME,root/'probe.big',screen.scenes_for(cls.model,assets),assets,script_factory=screen.script_factory(cls.model,assets),full_name=screen.FULL,template_cache=cls.template)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup();test_screen.NativeScreenTest.tearDownClass()
 def test_native_groups_artwork_and_profile_survive_data_only_rebuild(self):
  before=self.template.read_bytes();source=BigFile(self.template);output=Path(self.tmp.name)/'fast.big'
  template_renderer.build(self.template,output,script_factory=screen.script_factory(self.model,{}),full_name=screen.FULL)
  actual=BigFile(output);self.assertEqual(list(source.entries),list(actual.entries))
  for key in source.entries:
   if key!='0':self.assertEqual(source.entries[key].original,actual.entries[key].original,key)
  apt=AptFile(actual);self.assertEqual([],Actions(apt).read_all().errors)
  vm,state,_,_=open_native(output,full=screen.FULL);load_data(vm,state);self.assertEqual(len(self.model['people']),len(state.get('people')))
  vm.invoke(state.get('Command'),state,(40,));self.assertTrue(state.get('profile'));self.assertTrue(state.get('people')[state.get('person')][23]);self.assertEqual([],vm.errors)
  self.assertEqual(before,self.template.read_bytes())
 def test_repeated_data_refresh_does_not_keep_previous_career_labels(self):
  output=Path(self.tmp.name)/'next.big';first=copy.deepcopy(self.model);second=copy.deepcopy(self.model)
  first.update(clubName='Primeira carreira');second.update(clubName='Outra carreira')
  for model in (first,second):
   template_renderer.build(self.template,output,script_factory=screen.script_factory(model,{}),full_name=screen.FULL)
   vm,state,_,_=open_native(output,full=screen.FULL);load_data(vm,state)
   self.assertIn(model['clubName'],state.get('scene0').get('careerMeta').get('text'));self.assertEqual([],vm.errors)
 def test_chunk_reuse_keeps_native_wrapper_and_identical_decoded_bytes(self):
  source=BigFile(self.template);raw=source.original
  _,_,blocks=template_renderer.load(self.template,screen.FULL)
  wrapped,reused=template_renderer.wrap(raw,source.wrapper,blocks)
  self.assertGreater(reused,0);self.assertEqual(raw,chunk_unwrap(wrapped)[0])
 def test_damaged_template_is_rejected_before_publication(self):
  bad=Path(self.tmp.name)/'damaged.big';bad.write_bytes(self.template.read_bytes()+b'damaged')
  bad.with_suffix('.json').write_bytes(self.template.with_suffix('.json').read_bytes())
  with self.assertRaises(ValueError):template_renderer.build(bad,Path(self.tmp.name)/'rejected.big',script_factory=screen.script_factory(self.model,{}),full_name=screen.FULL)

if __name__=='__main__':unittest.main()
