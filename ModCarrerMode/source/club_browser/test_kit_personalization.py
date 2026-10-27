"""Regression: classic kit rows must not override the active kit's font."""
import unittest
import numpy as np
from roster_data import current_kits
from kit_personalization import surface

class KitTests(unittest.TestCase):
 def test_current_year_is_independent_of_database_order(self):
  current=dict(teamtechid=1043,teamkittypetechid=0,year=0,numberfonttype=201,numbercolor=7)
  classic=dict(current,year=1989,numberfonttype=248,numbercolor=13)
  other=dict(current,teamtechid=1,numberfonttype=225)
  for rows in ([current,classic,other],[classic,other,current]):
   self.assertEqual(current_kits(rows,1043),{0:current})
  self.assertEqual(current_kits([classic],1043),{})
  with self.assertRaises(ValueError):current_kits([current,dict(current,numberfonttype=8)],1043)
  first=dict(current,teamkitid=1685);later=dict(current,teamkitid=2607,numberfonttype=248)
  self.assertEqual(current_kits([later,first],1043),{0:first})

 def test_decals_keep_original_mesh_and_skeleton_weights(self):
  dtype=np.dtype([('p','<f4',3),('n','<f4',3),('uv','<f4',2),('j','<u2',8),('w','u1',8)])
  v=np.zeros(4,dtype=dtype);v['p']=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]];v['uv']=[[0,0],[1,0],[1,1],[0,1]];v['n']=[0,0,1];v['j'][:,0]=7;v['w'][:,0]=255
  source=dict(v=v,idx=np.array([0,1,2,0,2,3],dtype='<u4'),skinned=True);before=v.tobytes()
  for rect in ((.2,.2,.8,.8),(.8,.8,.2,.2)):
   out=surface(source,rect,3,'number');self.assertEqual(v.tobytes(),before);self.assertTrue(out['skinned']);self.assertEqual(out['texture'],3)
   self.assertTrue((out['v']['w'][:,0]==255).all());self.assertTrue((out['v']['j'][:,0]==7).all());self.assertTrue(np.isfinite(out['v']['p']).all());self.assertLess(out['idx'].max(),len(out['v']))

if __name__=='__main__':unittest.main()
