"""The shared plinth must not intersect the independently instanced locker bases."""
from pathlib import Path
import tempfile,unittest
import numpy as np
import room_v3 as room
import portable_paths
from room_interior_r72 import write_groups
from room_visual_r68 import read_mesh
from rx3 import Rx3,VERTEX,INDEX


class FooterTests(unittest.TestCase):
    def test_all_four_runs_have_floor_and_base_clearance(self):
        plinths=[v for v,_ in room.joinery_groups()['body'] if v['p'][:,1].max()<1100]
        self.assertEqual(len(plinths),4)
        base=room.bay_groups()['wood'][0][0]
        base_bottom=float(base['p'][:,1].min())+1000
        for p in plinths:
            self.assertGreaterEqual(float(p['p'][:,1].min())-1000,.49)
            self.assertGreaterEqual(base_bottom-float(p['p'][:,1].max()),.49)
            self.assertTrue(np.isfinite(p['p']).all())

    def test_plinth_end_caps_are_recessed_from_exposed_bank_ends(self):
        plinths=[v for v,_ in room.joinery_groups()['body'] if v['p'][:,1].max()<1100]
        for vertices,(_,center,width,normal) in zip(plinths,room.fascia_specs()):
            right=np.cross((0,1,0),normal)
            local=(vertices['p']-center)@right
            self.assertGreater(float(local.min()),-width/2+.39)
            self.assertLess(float(local.max()),width/2-.39)

    def test_native_joinery_changes_only_low_plinth_vertices(self):
        game=portable_paths.GAME;manifest=room.build_manifest(str(game))
        old=Rx3((game/room.PREFIX/manifest['model_files']['joinery.rx3']).read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'joinery.rx3'
            bindings=write_groups(game/room.OLD/'locker_support_r68.rx3',room.joinery_groups(),path)
            new=Rx3(path.read_bytes())
            self.assertEqual([b['material'] for b in bindings],['body','edge','cabinet'])
            for slot in range(len(bindings)):
                self.assertEqual(old.get(INDEX)[slot],new.get(INDEX)[slot])
                before,_=read_mesh(old,slot);after,_=read_mesh(new,slot)
                if slot:
                    self.assertEqual(before.tobytes(),after.tobytes())
                else:
                    high=(before['p'][:,1]>1100)|(after['p'][:,1]>1100)
                    self.assertEqual(before[high].tobytes(),after[high].tobytes())
                    self.assertEqual(before['n'].tobytes(),after['n'].tobytes())
                    self.assertEqual(before['uv'].tobytes(),after['uv'].tobytes())

    def test_slot_drawer_towels_and_shoes_base_are_unchanged(self):
        game=portable_paths.GAME;manifest=room.build_manifest(str(game))
        current=Rx3((game/room.PREFIX/manifest['model_files']['locker_bay.rx3']).read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'locker.rx3'
            write_groups(game/room.OLD/'locker_support_r68.rx3',room.bay_groups(),path)
            generated=Rx3(path.read_bytes())
            for kind in (VERTEX,INDEX):self.assertEqual(current.get(kind),generated.get(kind))


if __name__=='__main__':unittest.main()
