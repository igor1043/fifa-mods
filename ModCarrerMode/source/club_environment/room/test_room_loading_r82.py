"""Check loading coverage against the real room waiting camera."""
import tempfile,unittest
from pathlib import Path
import numpy as np
from rx3 import Rx3
from room_visual_r68 import read_mesh
import portable_paths as portable
import room_loading_r81 as loading

class LoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)
        cls.report=loading.stage(portable.GAME,cls.out)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def mesh(self,name):return read_mesh(Rx3((self.out/name).read_bytes()),0)[0]['p']
    def test_opaque_backdrop_covers_camera_frustum_in_all_supported_ratios(self):
        points=self.mesh('loading_backdrop_r83.rx3')
        eye=np.array((0,1187,750));forward=np.array((0,-7,-750),float);forward/=np.linalg.norm(forward)
        right=np.cross(forward,(0,1,0));right/=np.linalg.norm(right);up=np.cross(right,forward)
        for aspect in (.5,4/3,16/9,21/9,32/9,4):
            for x,y in ((-1,-1),(-1,1),(1,-1),(1,1)):
                ray=forward+np.tan(np.deg2rad(37))*(right*x*aspect+up*y)
                hit=eye+ray*((399-eye[2])/ray[2])
                self.assertTrue(np.all(hit[:2]>points[:,:2].min(0)) and np.all(hit[:2]<points[:,:2].max(0)),(aspect,hit))
    def test_badge_is_separate_sharp_geometry_and_aligned_to_card(self):
        points=self.mesh('loading_badge_r83.rx3')
        self.assertAlmostEqual(float(np.ptp(points[:,0])),loading.BADGE_SIZE,places=3)
        self.assertTrue(np.allclose(points.mean(0),(0,0,0)))
        self.assertAlmostEqual(loading.BADGE_X,-283.59375)
        self.assertAlmostEqual(loading.BADGE_Y,1270.71875)
    def test_revisioned_resources_do_not_replace_the_template(self):
        self.assertEqual(self.report['revision'],83)
        self.assertEqual(len(list(self.out.glob('*.rx3'))),14)
        for path in self.out.glob('*.rx3'):self.assertGreater(path.stat().st_size,100)

if __name__=='__main__':unittest.main()
