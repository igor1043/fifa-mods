from pathlib import Path
from tempfile import TemporaryDirectory
import json,random,unittest
from player_poses import select,CLIPS

class PlayerPoses(unittest.TestCase):
 def test_retired_walking_pose_is_replaced_even_for_a_persisted_request(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);req=dict(pid=1,seq=2,club=1043,player=158023)
   for name in (*CLIPS,'idle_shift_weight.json'):(root/name).write_text('{}')
   (root/'player-animation-choice.json').write_text(json.dumps(dict(request=[1,2,1043,158023],clip='idle_shift_weight.json')))
   self.assertNotIn('idle_shift_weight.json',CLIPS);self.assertIn(select(root,req,root).name,CLIPS)
 def test_entry_choices_vary_and_coach_state_remains_independent(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);clips=root/'clips';clips.mkdir()
   for name in CLIPS:(clips/name).write_text('{}')
   coach=root/'coach-animation-choice.json';coach.write_text('unchanged');req={'pid':9,'club':1043,'player':233206};rng=random.Random(10);choices=[]
   for seq in range(1,30):
    item=dict(req,seq=seq);chosen=select(root,item,clips,rng);self.assertEqual(chosen,select(root,item,clips,rng));choices.append(chosen.name)
   self.assertEqual(set(choices),set(CLIPS));self.assertTrue(all(a!=b for a,b in zip(choices,choices[1:])));self.assertEqual(coach.read_text(),'unchanged')
 def test_single_installed_clip_is_a_valid_fallback(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);(root/CLIPS[0]).write_text('{}');self.assertEqual(select(root,{'pid':1,'seq':1,'club':1043,'player':1},root).name,CLIPS[0])

if __name__=='__main__':unittest.main()
