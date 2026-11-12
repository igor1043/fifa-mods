"""Cabinet fit, collision footprints and retirement of the white trim."""
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import portable_paths
import room_v3 as room
import room_fitted_shell as shell
import room_annex_doors as doors
from room_visual_r68 import box,join,read_mesh,replace_mesh
from rx3 import Rx3


class FittedRoom(unittest.TestCase):
    def test_cabinet_backs_fit_wall_and_slots_do_not_move(self):
        game=portable_paths.GAME
        before=room.config(game)['layout'];layout=copy.deepcopy(before)
        origins=[room.frame(i,game)[0] for i in range(room.CAPACITY)]
        for i,origin in enumerate(origins):
            if i<12:self.assertAlmostEqual(abs(float(origin[2])-shell.BACK_INNER_Z)-2,1.5)
            else:self.assertAlmostEqual(shell.SIDE_INNER_X-abs(float(origin[0]))-2,1.5)
        self.assertEqual(before,layout)
        groups=room.joinery_groups();self.assertNotIn('light',groups)

    def test_edit_keeps_floor_roof_and_annex_meshes_byte_for_byte(self):
        game=portable_paths.GAME
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.rx3';path.write_bytes((game/room.OLD/'room_roles_r77.rx3').read_bytes())
            room.widen_main(path);rx=Rx3(path.read_bytes())
        before={i:read_mesh(rx,i) for i in (0,1,2,3,24)}
        result=shell.geometry(rx,'roles');self.assertIn('0',result)
        for slot in (2,3,24):
            a,b=before[slot];c,d=read_mesh(rx,slot)
            self.assertEqual(a.tobytes(),c.tobytes());self.assertEqual(b.tobytes(),d.tobytes())
        for slot in (0,1):
            a,ids=before[slot];c,ind=read_mesh(rx,slot)
            tri=ids.reshape(-1,3);mask=(a['p'][tri][:,:,2]>room.MAIN_END+.1).all(1)
            expected=sorted(a[t].tobytes() for t in tri[mask])
            tri=ind.reshape(-1,3);mask=(c['p'][tri][:,:,2]>room.MAIN_END+.1).all(1)
            self.assertEqual(expected,sorted(c[t].tobytes() for t in tri[mask]))
            self.assertTrue(np.isfinite(c['p']).all());self.assertLess(int(ind.max()),len(c))

    def test_service_wall_stays_straight_after_last_bay(self):
        lo,hi=(850,1000,-600),(862,1338,1542)
        template=portable_paths.GAME/room.OLD/'room_roles_r77.rx3'
        rx=Rx3(template.read_bytes());replace_mesh(rx,0,*box(lo,hi))
        shell.geometry(rx,'roles');v,ids=read_mesh(rx,0);p=v['p'][ids.reshape(-1,3)]
        near=p[(p[:,:,2]<=shell.CABINET_END_Z+.001).all(1)]
        far=p[(p[:,:,2]>=shell.CABINET_END_Z-.001).all(1)]
        self.assertAlmostEqual(float(near[:,:,0].min()),shell.SIDE_INNER_X)
        self.assertAlmostEqual(float(far[:,:,0].min()),shell.SIDE_INNER_X)
        self.assertEqual(shell.returns(),[])
        self.assertFalse(((np.ptp(p[:,:,0],axis=1)>.01)&(np.ptp(p[:,:,1],axis=1)>20)&(np.ptp(p[:,:,2],axis=1)>20)).any())

    def test_collision_follows_new_wall_and_retains_service_corridor_and_furniture(self):
        original=[dict(name='Limite externo',lo=[850,0,-600],hi=[862,320,1542]),
                  dict(name='Sala / parede de fundo',lo=[-856,0,-612],hi=[856,320,-600]),
                  dict(name='Maca',lo=[-670,0,1788],hi=[-446,110,1872])]
        before=copy.deepcopy(original);result=shell.obstacles(original)
        self.assertEqual(original,before);self.assertIn(original[-1],result)
        parts=[o for o in result if o['name']=='Limite externo']
        self.assertEqual(len(parts),1);self.assertEqual(parts[0]['lo'][0],shell.SIDE_INNER_X)
        self.assertFalse(any('fitted wall return' in item['name'] for item in result))
        back=next(o for o in result if o['name']=='Sala / parede de fundo')
        self.assertEqual(back['hi'][2],shell.BACK_INNER_Z)
        for name in ('ball trolley','next match board'):
            self.assertTrue(any(o['name']=='Current Dressing Room / '+name for o in result))

    def test_legacy_pale_lintel_is_removed_without_erasing_walls_or_new_sign(self):
        game=portable_paths.GAME;rx=Rx3((game/room.OLD/'room_roles_r77.rx3').read_bytes())
        before,ids=read_mesh(rx,0);tri=ids.reshape(-1,3);drop=doors.fixture_mask(before,ids)
        self.assertEqual(int(drop.sum()),4)
        counts=doors.strip_old_fixtures(rx,'roles');self.assertEqual(counts['0'],4)
        after,ind=read_mesh(rx,0)
        self.assertEqual(sorted(before[t].tobytes() for t in tri[~drop]),
                         sorted(after[t].tobytes() for t in ind.reshape(-1,3)))


if __name__=='__main__':unittest.main()
