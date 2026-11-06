"""Camera-side visibility and open entrances of the retained annex shells."""
import json,unittest
import numpy as np
from rx3 import Rx3
from room_visual_r68 import read_mesh,box
from room_v3 import annex_surfaces,OLD
import portable_paths as portable


def hits(vertices,indices,origin,direction):
    tri=vertices['p'][indices.reshape(-1,3)].astype(float)
    e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
    h=np.cross(direction,e2);det=(e1*h).sum(1)
    # Match one-sided native materials: a back-facing triangle must not count.
    mask=det>1e-8
    inv=np.zeros(len(det));inv[mask]=1/det[mask]
    s=np.array(origin)-tri[:,0];u=inv*(s*h).sum(1)
    q=np.cross(s,e1);v=inv*(q*direction).sum(1);t=inv*(e2*q).sum(1)
    return t[mask&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>0)]


class AnnexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=portable.GAME/OLD
        rx=Rx3((base/'interior_r78.rx3').read_bytes())
        spec=json.loads((base/'interior_r78.json').read_text(encoding='utf8'))
        cls.parts=[]
        for i,b in enumerate(spec['bindings']):
            if b['material'].startswith('secondary_wall_'):
                original,ids=read_mesh(rx,i);v,indices=annex_surfaces(original,ids)
                cls.parts.append((v,indices))
    def test_retains_real_annex_geometry_instead_of_empty_submeshes(self):
        for v,indices in self.parts:
            self.assertEqual(indices.ndim,1,'RX3 index headers count individual indices, not triangle rows')
            self.assertGreater(len(indices),100)
            self.assertGreaterEqual(v['p'][:,2].min(),1544)
            self.assertLess(len(v),65536)
            self.assertTrue(np.isfinite(v['p']).all())
    def test_solid_walls_visible_from_inside_and_outside_both_rooms(self):
        v,indices=self.parts[0]
        for origin,direction in [
            ((180,1180,2000),(-1,0,0)),((180,1180,2000),(1,0,0)),((180,1180,2000),(0,0,1)),
            ((-725,1180,2200),(-1,0,0)),((-725,1180,2200),(1,0,0)),((-725,1180,2200),(0,0,1)),
            ((900,1180,2000),(-1,0,0)),((-1200,1180,2200),(1,0,0))]:
            self.assertGreater(len(hits(v,indices,origin,direction)),0,(origin,direction))
    def test_no_new_surface_blocks_the_two_entrances(self):
        for x in (180,-545):
            for v,indices in self.parts:
                distances=hits(v,indices,(x,1120,1600),(0,0,-1))
                self.assertFalse(any(t<100 for t in distances),(x,distances))
    def test_main_room_replacement_is_still_removed(self):
        v,indices=annex_surfaces(*box((700,1000,755),(750,1300,1500)))
        self.assertTrue(np.all(v['p'][:,1]==900))


if __name__=='__main__':unittest.main()
