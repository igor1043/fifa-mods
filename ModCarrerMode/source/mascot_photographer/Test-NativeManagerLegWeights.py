"""Regression: opposite-thigh bleed, central continuity and protected regions."""
from pathlib import Path
import importlib.util,unittest
import numpy as np

spec=importlib.util.spec_from_file_location('leg_review',Path(__file__).with_name('Repair-NativeManagerLegWeights.py'));review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)

class LegWeights(unittest.TestCase):
    def setUp(self):
        self.ref=np.array([[side*(8+k*.1),75+k*.1,0] for side in [-1,1] for k in range(24)],dtype=float);self.mass=np.zeros((len(self.ref),31));self.mass[:24,3]=1;self.mass[24:,7]=1
    def test_inner_thigh_no_longer_follows_the_opposite_leg(self):
        xyz=np.array([[-8,78,0],[8,78,0]],dtype=float);original=np.zeros((2,31));original[:,3]=original[:,7]=.5;out,_=review.reviewed_field(xyz,original,self.ref,self.mass,np.ones(2,bool));self.assertLess(out[0,7],.05);self.assertLess(out[1,3],.05);np.testing.assert_allclose(out.sum(1),1)
    def test_shoes_calves_torso_and_other_uv_charts_keep_their_skin(self):
        xyz=np.array([[8,0,0],[8,40,0],[8,110,0],[8,78,0]],dtype=float);original=np.zeros((4,31));original[:,2]=1;out,_=review.reviewed_field(xyz,original,self.ref,self.mass,np.array([True,True,True,False]));np.testing.assert_array_equal(out,original)
    def test_centre_seam_stays_continuous(self):
        xyz=np.array([[-.001,78,0],[.001,78,0]],dtype=float);original=np.zeros((2,31));original[:,3]=original[:,7]=.5;out,_=review.reviewed_field(xyz,original,self.ref,self.mass,np.ones(2,bool));self.assertLess(np.max(abs(out[0]-out[1])),.002);np.testing.assert_allclose(out.sum(1),1)

if __name__=='__main__':unittest.main()
