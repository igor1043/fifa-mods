"""Verify native ceiling/support meshes against the installed room template."""
from pathlib import Path
import tempfile, unittest
import numpy as np
from rx3 import Rx3, VERTEX
from room_visual_r68 import stage, read_mesh, MODULE, PREFIX
import portable_paths


class RoomGeometryTests(unittest.TestCase):
    def test_native_geometry_and_ceiling_grid(self):
        source=portable_paths.GAME/PREFIX/'room_roles_r62.rx3'
        before=source.read_bytes();original=Rx3(before)
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder);info=stage(portable_paths.GAME,output)
            new=Rx3((output/info['geometry']).read_bytes())
            self.assertEqual(original.names(),new.names())
            ceiling,indices=read_mesh(new,3)
            self.assertLess(np.max(np.abs(ceiling['uv'].astype(float)-ceiling['p'][:,[0,2]]/MODULE)),.02)
            for x,z in info['lights']:
                self.assertEqual(x%60,30);self.assertEqual(z%60,0)
                self.assertFalse(x< -330 and z>942)
            for slot in range(len(original.get(VERTEX))):
                if slot not in (3,4,5):self.assertEqual(original.get(VERTEX)[slot],new.get(VERTEX)[slot])
                vertices,indices=read_mesh(new,slot)
                self.assertLess(indices.max(),len(vertices));self.assertTrue(np.isfinite(vertices['p']).all())
            support=Rx3((output/info['support']).read_bytes());vertices,indices=read_mesh(support,0)
            self.assertEqual(len(support.get(VERTEX)),1)
            self.assertLessEqual(vertices['p'][:,2].min(),-5)
            self.assertGreaterEqual(vertices['p'][:,2].max(),33)
            self.assertLessEqual(vertices['p'][:,0].min(),-34)
            self.assertGreaterEqual(vertices['p'][:,0].max(),34)
        self.assertEqual(before,source.read_bytes())


if __name__=='__main__':unittest.main()
