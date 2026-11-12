from pathlib import Path
import unittest,numpy as np
from rx3 import Rx3,VERTEX,INDEX
from room_visual_r68 import read_mesh
import portable_paths as portable
import room_v3,room_hydration_wall as wall

def front_hit(vertices,indices,x,y):
    p=vertices['p'][indices.reshape(-1,3)];a=p[:,1]-p[:,0];b=p[:,2]-p[:,0]
    normal=np.cross(a,b);direction=np.array([0.,0.,1.]);h=np.cross(direction,b);det=(a*h).sum(1)
    valid=(np.abs(det)>1e-6)&(normal[:,2]<0);inv=np.divide(1.,det,out=np.zeros_like(det),where=valid)
    s=np.array([x,y,1450.])-p[:,0];u=inv*(s*h).sum(1);q=np.cross(s,a);v=inv*q[:,2];t=inv*(b*q).sum(1)
    return t[valid&(u>=-1e-5)&(v>=-1e-5)&(u+v<=1.00001)&(t>0)&(t<120)]

class HydrationWall(unittest.TestCase):
    def setUp(self):
        self.rx=Rx3((portable.GAME/room_v3.OLD/'room_roles_r77.rx3').read_bytes())
    def test_closes_the_side_opening_and_upper_strip_with_front_faces(self):
        before,indices=read_mesh(self.rx,0)
        self.assertEqual(len(front_hit(before,indices,800,1100)),0)
        report=wall.repair(self.rx);self.assertGreater(report['original_faces_removed'],0)
        vertices,indices=read_mesh(self.rx,0)
        for x in (252,300,500,680,700,750,800,830):
            for y in (1010,1050,1120,1200,1300,1330):
                hit=front_hit(vertices,indices,x,y);self.assertGreater(len(hit),0,(x,y))
                self.assertAlmostEqual(float(hit.min()+1450),wall.SIDE_END_Z,places=3)
        self.assertEqual(len(front_hit(vertices,indices,180,1180)),0)
    def test_preserves_other_triangles_submeshes_and_is_idempotent(self):
        before,indices=read_mesh(self.rx,0);tri=indices.reshape(-1,3);keep=~wall.legacy_faces(before,indices)
        expected=sorted(before[t].tobytes() for t in tri[keep])
        submeshes=[read_mesh(self.rx,i) for i in range(1,len(self.rx.get(VERTEX)))]
        wall.repair(self.rx);after,new_indices=read_mesh(self.rx,0)
        self.assertEqual(expected,sorted(after[t].tobytes() for t in new_indices.reshape(-1,3)[:-12]))
        for i,(v,idx) in enumerate(submeshes,1):
            actual,actual_idx=read_mesh(self.rx,i);self.assertEqual(v.tobytes(),actual.tobytes());self.assertEqual(idx.tobytes(),actual_idx.tobytes())
        first=self.rx.build();wall.repair(self.rx);self.assertEqual(first,self.rx.build())
    def test_office_rebase_retains_the_complete_solid_wall(self):
        from room_pes_office import merge_main_shell
        original=self.rx.build();wall.repair(self.rx)
        merged=merge_main_shell(Rx3(original),self.rx)
        vertices,indices=read_mesh(merged,0)
        self.assertTrue(wall.front_present(vertices,indices,1338.))
        first=merged.build();wall.repair(merged);self.assertEqual(first,merged.build())
        self.assertGreater(len(front_hit(vertices,indices,800,1330)),0)
if __name__=='__main__':unittest.main()
