"""Physical ceiling openings, contact-plane regressions and scoped walls."""
import unittest
from pathlib import Path
import numpy as np
import portable_paths
import room_v3 as room
import room_ceiling as ceiling
import room_exit_door as door
from room_visual_r68 import read_mesh,join
from rx3 import Rx3


class CeilingTests(unittest.TestCase):
    def test_openings_follow_the_same_world_grid_as_the_tiles(self):
        self.assertEqual(len(ceiling.LIGHTS),12)
        self.assertEqual(len(ceiling.SUPPLY),2)
        self.assertEqual(len(ceiling.RETURN),1)
        self.assertEqual(len(ceiling.SPRINKLERS),6)
        for opening in ceiling.openings():
            for coordinate in opening:self.assertAlmostEqual(coordinate/60,round(coordinate/60))
        for i,(a,b,c,d) in enumerate(ceiling.openings()):
            for aa,bb,cc,dd in ceiling.openings()[:i]:
                self.assertTrue(b<=aa or bb<=a or d<=cc or dd<=c)

    def test_roof_has_true_openings_and_an_unskewed_sixty_cm_texture_grid(self):
        v,ids=ceiling.tiles(room.CEILING_Y,room.MAIN_END)
        p=v['p'][ids.reshape(-1,3)].astype(float)
        bottom=p[(np.abs(p[:,:,1]-room.CEILING_Y)<.001).all(1)]
        area=np.linalg.norm(np.cross(bottom[:,1]-bottom[:,0],bottom[:,2]-bottom[:,0]),axis=1).sum()/2
        expected=1700*(room.MAIN_END+600)-sum((b-a)*(d-c) for a,b,c,d in ceiling.openings())
        self.assertAlmostEqual(area,expected,delta=2.)
        for a,b,c,d in ceiling.openings():
            centers=bottom.mean(1)
            self.assertFalse(((centers[:,0]>a)&(centers[:,0]<b)&(centers[:,2]>c)&(centers[:,2]<d)).any())
        np.testing.assert_allclose(v['uv'],v['p'][:,[0,2]]/60,atol=.02)
        self.assertLess(len(v),65536)

    def test_native_annex_ceiling_triangles_survive_replacement_byte_for_byte(self):
        game=portable_paths.GAME;manifest=room.build_manifest(str(game))
        rx=Rx3((game/room.PREFIX/manifest['model_files']['room_roles.rx3']).read_bytes())
        before,ids=read_mesh(rx,3);tri=ids.reshape(-1,3)
        keep=~((before['p'][tri][:,:,2]<=room.MAIN_END+.001).all(1)&
               (before['p'][tri][:,:,1]>=1310).all(1))
        expected=sorted(before[t].tobytes() for t in tri[keep])
        ceiling.replace_main_ceiling(rx,room.CEILING_Y,room.MAIN_END)
        after,ids=read_mesh(rx,3);tri=ids.reshape(-1,3)
        kept=after['p'][tri][:,:,2].min(1)>room.MAIN_END+.001
        # All installed non-main ceiling faces belong to the retained annexes.
        self.assertEqual(expected,sorted(after[t].tobytes() for t in tri[kept]))

    def test_recessed_fittings_and_small_pendant_sprinklers_fit_the_native_format(self):
        groups=ceiling.geometry(room.CEILING_Y)
        for key,parts in groups.items():
            v,ids=join(parts)
            self.assertLess(len(v),65536)
            self.assertLess(int(ids.max()),len(v))
            self.assertTrue(np.isfinite(v['p']).all())
            self.assertGreaterEqual(float(v['p'][:,1].min()),room.CEILING_Y-6.31)
            self.assertLessEqual(float(v['p'][:,1].max()),room.CEILING_Y+6.51)
            def unpack(bits):
                raw=np.stack([(bits.astype(np.int64)>>s)&1023 for s in (0,10,20)],axis=1)
                return np.where(raw>=512,raw-1024,raw)/511
            self.assertLess(np.abs((unpack(v['n'])*unpack(v['g'])).sum(1)).max(),.005,key)
        lens,_=join(groups['diffuser'])
        self.assertGreater(float(lens['p'][:,1].min()),room.CEILING_Y+4)

    def test_terminal_walls_are_whole_white_panels_with_a_fitted_exit_opening(self):
        v,ids=join(room.plain_wall_panels());p=v['p'][ids.reshape(-1,3)]
        self.assertEqual({round(float(x),1) for x in v['p'][:,0]},{-847.7,847.7})
        self.assertAlmostEqual(float(v['p'][:,2].min()),735.)
        self.assertAlmostEqual(float(v['p'][:,2].max()),room.MAIN_END,places=3)
        self.assertAlmostEqual(float(v['p'][:,1].min()),1000.)
        self.assertAlmostEqual(float(v['p'][:,1].max()),room.CEILING_Y)
        left=p[p[:,:,0].mean(1)<0];center=left.mean(1)
        self.assertFalse(((center[:,2]>door.CENTER_Z-85)&(center[:,2]<door.CENTER_Z+85)&(center[:,1]<1242)).any())
        self.assertEqual(len(room.plain_wall_panels()),4)
        self.assertEqual(door.CENTER_Z,1350.)

    def test_cornice_does_not_render_the_shared_white_green_contact_planes(self):
        groups=room.joinery_groups()
        for key,levels in [('body',(1287.,1332.,1334.5,room.CEILING_Y)),('edge',(1287.,))]:
            v,ids=join(groups[key]);y=v['p'][ids.reshape(-1,3)][:,:,1]
            for level in levels:self.assertFalse((np.abs(y-level)<.005).all(1).any(),(key,level))
        # Front artwork keeps its dimensions and anchors.
        banks=room.fascia_specs()
        self.assertEqual(banks[0][1],[-405,1309.5,-507.5])
        self.assertEqual(banks[1][1],[405,1309.5,-507.5])


if __name__=='__main__':unittest.main(verbosity=2)
