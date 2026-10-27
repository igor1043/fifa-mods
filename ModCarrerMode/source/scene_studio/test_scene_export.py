"""Real fixture tests: skinning, transformed duplicate, validation and native RX3."""
from pathlib import Path
import copy,json,struct,tempfile,unittest,zipfile
import numpy as np
from scene_export import ROOT,validate_scene,actor_parts,write_model,read_model,export_package

class SceneExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.scene=json.loads((ROOT/'build/tests/baseline-scene.json').read_text(encoding='utf8'))
    def test_original_pose_reproduced(self):
        expected,_=read_model(ROOT/'assets/baseline.ff3d');index=0;error=0
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            path=Path(folder)/'scene.ff3d';parts,textures=write_model(self.scene,path);actual,images=read_model(path)
            self.assertEqual(parts,108);self.assertEqual(len(actual),len(expected));self.assertLessEqual(textures,256)
            for row,want in zip(actual,expected):
                error=max(error,float(abs(row['v']['p']-want['v']['p']).max()));self.assertTrue(np.array_equal(row['idx'],want['idx']))
                self.assertTrue(np.allclose(np.linalg.norm(row['v']['n'],axis=1),1,atol=.001))
            self.assertLess(error,.003)
        print('baseline native round trip max error cm:',error)
    def test_transform_and_duplicate(self):
        actor=copy.deepcopy(self.scene['actors'][0]);base,_=actor_parts(actor);actor['position'][0]+=1;actor['id']='copy'
        moved,_=actor_parts(actor)
        for a,b in zip(base,moved):self.assertTrue(np.allclose(b['v']['p']-a['v']['p'],[100,0,0],atol=.001))
        actor['quaternion']=[0,0,1,0];actor['scale']=[.02,.02,.02];rotated,_=actor_parts(actor)
        center=np.array(actor['position'])*100
        for a,b in zip(base,rotated):
            relative=a['v']['p']-np.array(self.scene['actors'][0]['position'])*100
            self.assertTrue(np.allclose(b['v']['p'],relative*np.array([-2,-2,2])+center,atol=.003))
        valid=copy.deepcopy(self.scene);valid['actors'].append(actor);validate_scene(valid)
    def test_rejects_invalid_scene(self):
        edits=[lambda s:s.update(schema=99),lambda s:s.update(actors=[]),lambda s:s['actors'].append(copy.deepcopy(s['actors'][0])),lambda s:s['actors'][0].update(playerId=0),lambda s:s['actors'][0].update(quaternion=[0,0,0,0]),lambda s:s['actors'][0]['bones'][0].update(name='Fake'),lambda s:s['actors'][0]['position'].__setitem__(0,float('inf')),lambda s:s['actors'][0]['bones'][0]['scale'].__setitem__(0,0)]
        for edit in edits:
            scene=copy.deepcopy(self.scene);edit(scene)
            with self.assertRaises(ValueError):validate_scene(scene)
    def test_native_package(self):
        # One actor exercises RX3 conversion/materials without duplicating a full
        # team in the test output. The full team geometry is tested above.
        scene=copy.deepcopy(self.scene);scene['actors']=scene['actors'][:1]
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            out=Path(folder)/'export';result=export_package(scene,out,json.loads((ROOT/'settings.json').read_text())['game_root'])
            self.assertGreater(result['vertices'],1000)
            with zipfile.ZipFile(result['archive']) as archive:
                self.assertIsNone(archive.testzip());self.assertIn('native/geometry.rx3',archive.namelist());self.assertIn('scene.json',archive.namelist())
            from native_assets import Rx3,VERTEX
            geometry=Rx3((out/'native/geometry.rx3').read_bytes());self.assertEqual(len(geometry.get(VERTEX)),96)
            manifest=json.loads((out/'native/assets.json').read_text());self.assertEqual(manifest['slots'],96)
            for page,blend in manifest['bindings']:self.assertTrue((out/'native'/f'atlas_{page}.rx3').is_file())
    def test_ik_resolved_pose_exports(self):
        scene=json.loads((ROOT/'build/tests/ik-scene.json').read_text(encoding='utf8'));validate_scene(scene)
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            path=Path(folder)/'ik.ff3d';write_model(scene,path);actual,_=read_model(path);baseline,_=read_model(ROOT/'assets/baseline.ff3d')
            from scene_export import rig
            boundary=len(rig(scene['actors'][0]['playerId'])['parts'])
            self.assertTrue(any(not np.allclose(a['v']['p'],b['v']['p'],atol=.001) for a,b in zip(actual[:boundary],baseline[:boundary])))
            for a,b in zip(actual[boundary:],baseline[boundary:]):self.assertTrue(np.allclose(a['v']['p'],b['v']['p'],atol=.001))
            self.assertTrue(all(np.isfinite(p['v'].view('<f4')).all() for p in actual))

if __name__=='__main__':unittest.main(verbosity=2)
