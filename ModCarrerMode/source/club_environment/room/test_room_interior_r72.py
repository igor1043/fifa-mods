"""Room-extension regressions against the native assets that will be installed."""
from pathlib import Path
import copy, json, os, tempfile, unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import portable_paths as portable
from rx3 import Rx3,VERTEX
from room_visual_r68 import read_mesh
import room_interior_r72 as room
from room_interior_r71 import decode_texture
from room_collision_r70 import solid_obstacles


class ExpandedRoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.stage=Path(os.environ.get('ROOM_REVIEW_STAGE',str(portable.GAME/room.PREFIX)))

    def test_every_native_mesh_buffer_finite_and_nonempty(self):
        for name in ['room_roles','scenery','medical_room','crest_surfaces','floor_shadows','interior','water_cooler']:
            rx=Rx3((self.stage/f'{name}_r72.rx3').read_bytes())
            for slot in range(len(rx.get(VERTEX))):
                v,idx=read_mesh(rx,slot);self.assertGreater(len(v),0);self.assertEqual(len(idx)%3,0)
                self.assertLess(int(idx.max()),len(v));self.assertTrue(np.isfinite(v['p']).all());self.assertTrue(np.isfinite(v['uv']).all())

    def test_extension_preserves_locker_positions_and_moves_services(self):
        rx=Rx3((self.stage/'room_roles_r72.rx3').read_bytes());before=Rx3((portable.GAME/room.PREFIX/'room_roles_r71.rx3').read_bytes())
        # Seat/cushion and locker solid roles have no newly added objects.
        for slot in [0,1,6,7,8,9]:
            old,_=read_mesh(before,slot);new,_=read_mesh(rx,slot)
            self.assertEqual(len(old),len(new));expected=old['p'].copy();expected[:,2]+=np.where(expected[:,2]>=room.CUT,room.EXTENSION,0)
            np.testing.assert_allclose(new['p'],expected,atol=.001)

    def test_signs_match_door_width_and_texture_aspect(self):
        rx=Rx3((self.stage/'medical_room_r72.rx3').read_bytes())
        for slot,center in [(6,-545),(7,180)]:
            v,_=read_mesh(rx,slot);lo=v['p'].min(0);hi=v['p'].max(0)
            self.assertAlmostEqual(float(hi[0]-lo[0]),132);self.assertAlmostEqual(float(hi[1]-lo[1]),33)
            self.assertAlmostEqual(float((hi[0]+lo[0])*.5),center);self.assertGreater(float(lo[1]),1240)
            self.assertAlmostEqual(float(lo[2]),1302.2,places=2)

    def test_floor_and_ceiling_keep_square_texture_grid(self):
        for model,slots in [('room_roles',[2,3]),('medical_room',[3])]:
            rx=Rx3((self.stage/f'{model}_r72.rx3').read_bytes())
            for slot in slots:
                v,_=read_mesh(rx,slot);self.assertLess(float(np.max(np.abs(v['uv'].astype(float)-v['p'][:,[0,2]]/60))),.025)

    def test_cameras_and_colliders_share_the_same_new_coordinates(self):
        d=json.loads((self.stage/'room_layout_r72.json').read_text(encoding='utf8'))
        old=json.loads((portable.GAME/'ModCarrerMode/data/club_environment/room/runtime/medical_room_r57.json').read_text())
        self.assertEqual(d['extension_cm'],360);self.assertEqual(d['room']['camera_bounds']['front'],1310)
        self.assertEqual(d['medical']['room_bounds']['hi'][2],2112)
        for a,b in zip(old['navigation'],d['medical']['navigation']):
            for index in [2,5]:self.assertEqual(b[index],room.shifted(a[index]))
            for index in [0,1,3,4,6]:self.assertEqual(a[index],b[index])
        for a,b in zip(old['obstacles'],d['medical']['obstacles']):
            self.assertEqual(a['name'],b['name'])
            for key in ['lo','hi']:
                self.assertEqual(a[key][:2],b[key][:2]);self.assertEqual(b[key][2],room.shifted(a[key][2]))

    def test_new_hall_has_clear_walkable_space(self):
        d=json.loads((self.stage/'room_layout_r72.json').read_text(encoding='utf8'));spec=json.loads((self.stage/'interior_r72.json').read_text())
        boxes=solid_obstacles([b for b in d['room']['obstacles']+d['medical']['obstacles'] if not b['name'].startswith('Hidratação /')]+spec['obstacles'])
        for z in [850,950,1050,1150]:
            point=np.array([0.,100.,float(z)])
            for box in boxes:
                lo=np.array(box['lo']);hi=np.array(box['hi']);nearest=np.clip(point,lo,hi)
                self.assertGreaterEqual(float(np.linalg.norm(point-nearest)),23,(z,box['name']))

    def test_cooler_conversion_real_scale_two_materials_and_license_geometry(self):
        rx=Rx3((self.stage/'water_cooler_r72.rx3').read_bytes());self.assertEqual(len(rx.get(VERTEX)),2);points=[];tris=0
        for i in [0,1]:
            v,idx=read_mesh(rx,i);points.append(v['p']);tris+=len(idx)//3
        p=np.concatenate(points);self.assertEqual(tris,10144)
        self.assertGreater(p[:,1].max()-p[:,1].min(),130);self.assertLess(p[:,1].max()-p[:,1].min(),145)
        self.assertGreaterEqual(float(p[:,2].min()),1243);self.assertLessEqual(float(p[:,2].max()),1300)

    def test_hydration_colors_do_not_change_to_team_colors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);live=root/room.PREFIX;live.mkdir(parents=True)
            spec=dict(bindings=[dict(material=k,submesh='room_part_1') for k in ['primary','orange_plastic','drink_amber','drink_red']],cooler_bindings=[])
            (live/'interior_r72.json').write_text(json.dumps(spec));samples=[]
            for ident,colors in [(1,[[1,0,0],[0,0,0]]),(2,[[1,1,0],[1,1,1]])]:
                captures={}
                def add(key,model,texture,name,*args,**kwargs):captures[key]=texture
                def missing(path):raise FileNotFoundError(path)
                with patch.object(portable,'GAME',root):room.prepare(dict(club=ident,club_name='Teste',colors=colors),missing,add,np.eye(4).reshape(-1).tolist())
                samples.append({key:np.array(decode_texture(root/path))[0,0,:3] for key,path in captures.items()})
            for key in ['interior_orange_plastic','interior_drink_amber','interior_drink_red']:np.testing.assert_array_equal(samples[0][key],samples[1][key])
            self.assertFalse(np.array_equal(samples[0]['interior_primary'],samples[1]['interior_primary']))


if __name__=='__main__':unittest.main()
