import json,random,tempfile,unittest
from pathlib import Path
from coach_animation import select,CLIPS

class CoachAnimation(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.clips=self.root/'clips';self.clips.mkdir();self.req={'pid':9,'seq':1,'club':383}
  for name in CLIPS:(self.clips/name).write_text('{}')
 def test_same_request_keeps_its_clip(self):
  first=select(self.root,self.req,self.clips,random.Random(3));self.assertEqual(first,select(self.root,self.req,self.clips,random.Random(9)))
 def test_new_entries_vary_without_adjacent_repeats(self):
  names=[];rng=random.Random(4)
  for seq in range(1,31):names.append(select(self.root,dict(self.req,seq=seq),self.clips,rng).name)
  self.assertEqual(set(names),set(CLIPS));self.assertTrue(all(a!=b for a,b in zip(names,names[1:])))
 def test_single_clip_still_works(self):
  for name in CLIPS[1:]:(self.clips/name).unlink()
  for seq in [1,2]:self.assertEqual(select(self.root,dict(self.req,seq=seq),self.clips).name,CLIPS[0])
 def test_invalid_state_is_replaced(self):
  state=self.root/'coach-animation-choice.json'
  for value in ['invalid','[]','null']:
   state.write_text(value);self.assertTrue(select(self.root,self.req,self.clips).is_file());self.assertEqual(json.loads(state.read_text())['schema'],1)
 def test_no_installed_clip_is_explicit(self):
  for name in CLIPS:(self.clips/name).unlink()
  with self.assertRaises(FileNotFoundError):select(self.root,self.req,self.clips)

if __name__=='__main__':unittest.main()
