from pathlib import Path
import copy,importlib.util,json,struct,tempfile,unittest
from pose_profile import signature

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare_pose',HERE/'exporter/prepare_pose.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
DATA=HERE.parents[1]/'data/club_browser/poses'
class AuthoredPoseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=json.loads((DATA/'starting_eleven.scene.json').read_text(encoding='utf-8-sig'));cls.reference=json.loads((HERE/'exporter/pose_reference.json').read_text(encoding='utf8'))
    def test_authored_file_is_reproducible(self):
        data=builder.compile_pose(self.scene,self.reference)
        self.assertEqual(data,(DATA/'starting_eleven.pose').read_bytes());self.assertEqual(struct.unpack_from('<8sII',data),(b'FFPOSE02',11,400))
    def test_invalid_or_partial_scene_rejected(self):
        edits=[lambda s:s.update(schema=99),lambda s:s['actors'].pop(),lambda s:s['actors'].__setitem__(1,copy.deepcopy(s['actors'][0])),lambda s:s['actors'][0]['bones'][0].update(name='Fake'),lambda s:s['actors'][0]['bones'][0].update(quaternion=[0,0,0,0]),lambda s:s['actors'][0]['position'].__setitem__(0,float('nan')),lambda s:s['actors'][0]['bones'][0]['scale'].__setitem__(0,0)]
        for edit in edits:
            value=copy.deepcopy(self.scene);edit(value)
            with self.assertRaises(ValueError):builder.compile_pose(value,self.reference)
    def test_pose_content_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            game=Path(directory);target=game/'ModCarrerMode/data/club_browser/poses/starting_eleven.pose';self.assertEqual(signature(game),b'legacy-pose');target.parent.mkdir(parents=True)
            data=builder.compile_pose(self.scene,self.reference);target.write_bytes(data);before=signature(game)
            changed=copy.deepcopy(self.scene);changed['actors'][0]['bones'][116]['quaternion']=[0,0,0,1];target.write_bytes(builder.compile_pose(changed,self.reference));self.assertNotEqual(signature(game),before)
            target.write_bytes(b'FFPOSE00'+data[8:])
            with self.assertRaises(ValueError):signature(game)
    def test_missing_or_old_complement_has_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            game=Path(directory);folder=game/'ModCarrerMode/data/club_browser/poses';folder.mkdir(parents=True)
            target=folder/'starting_eleven.pose';metadata=folder/'starting_eleven.json'
            metadata.write_text(json.dumps({'recipe_sha256':'0'*64}))
            with self.assertRaisesRegex(ValueError,'Falta a pose'):signature(game)
            target.write_bytes(builder.compile_pose(self.scene,self.reference))
            with self.assertRaisesRegex(ValueError,'desatualizada'):signature(game)
if __name__=='__main__':unittest.main(verbosity=2)
