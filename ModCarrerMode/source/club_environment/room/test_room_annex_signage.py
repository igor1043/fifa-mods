import json,unittest
import numpy as np
from rx3 import Rx3,VERTEX
from room_visual_r68 import read_mesh
import portable_paths as portable
import room_annex_signage as signs
import room_v3


class AnnexSignageTests(unittest.TestCase):
    def source(self,name):
        root=portable.GAME/room_v3.PREFIX
        files=json.loads((root/'manifest.json').read_text())['model_files']
        return Rx3((root/files[name]).read_bytes())

    def test_only_coloured_extra_lintel_is_removed_and_the_white_wall_remains(self):
        rx=self.source('interior.rx3');before=[read_mesh(rx,i) for i in range(len(rx.get(VERTEX)))]
        self.assertEqual(12,signs.clean_interior(rx))
        for slot,(v,idx) in enumerate(before):
            triangles=idx.reshape(-1,3)
            if slot==25:triangles=triangles[~signs.medical_backing(v,idx)]
            after,indices=read_mesh(rx,slot)
            self.assertEqual(sorted(v[t].tobytes() for t in triangles),sorted(after[t].tobytes() for t in indices.reshape(-1,3)),slot)
        self.assertEqual(0,signs.clean_interior(rx))
        roles=self.source('room_roles.rx3');v,ids=read_mesh(roles,0);points=v['p'][ids.reshape(-1,3)]
        # White lintel behind the removed decorative box still encloses the wall.
        self.assertTrue((((points[:,:,[0,1,2]]>=[-610,1238,1546.9]) &
                          (points<=[-480,1320,1557.1])).all((1,2))).any())

    def test_backing_fits_the_exact_main_plaque_without_moving_door_parts(self):
        rx=self.source('exit_door.rx3');before=[read_mesh(rx,i) for i in range(len(rx.get(VERTEX)))]
        self.assertEqual(48,signs.fit_supports(rx))
        for slot,(v,idx) in enumerate(before):
            after,indices=read_mesh(rx,slot);self.assertEqual(idx.tobytes(),indices.tobytes())
            if slot!=1:self.assertEqual(v.tobytes(),after.tobytes())
        v,_=read_mesh(rx,1)
        for center in (-545.,180.):
            p=v['p'];q=p[(p[:,1]>1243)&(p[:,1]<1279)&(abs(p[:,0]-center)<67)]
            self.assertTrue(np.allclose(q.min(0),[center-66,1244.5,1542.6],atol=.002))
            self.assertTrue(np.allclose(q.max(0),[center+66,1277.5,1545.3],atol=.002))
        self.assertEqual(0,signs.fit_supports(rx))
