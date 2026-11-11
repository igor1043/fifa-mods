import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import room_coach_office as office
import room_pes_office
import room_coach_art_r76 as art
from room_visual_r68 import box,join,read_mesh


class ProfessionalOfficeTests(unittest.TestCase):
    def test_furniture_move_preserves_uvs_and_corrects_positions_normals_and_tangents(self):
        v,ids=box((225,1000,2270),(475,1141,2370));before=v.copy()
        out=office.move(v,office.DESK)
        np.testing.assert_array_equal(v,before)
        np.testing.assert_allclose(out['p'],before['p']+[-90,0,-70])
        np.testing.assert_array_equal(out['uv'],before['uv'])
        np.testing.assert_array_equal(out['n'],before['n'])
        n,g=office.unpack(out['n']),office.unpack(out['g'])
        self.assertLess(np.abs((n*g).sum(1)).max(),.005)

    def test_meeting_corner_is_compact_and_does_not_block_the_entrance(self):
        from build_room_equipment import native_box
        bounds=native_box([-190,0,1928],[50,90,2267],*office.SEATING)
        self.assertGreater(bounds['lo'][0],400)
        self.assertGreater(bounds['lo'][2],1740)
        self.assertLess(bounds['hi'][0],750)
        self.assertLess(bounds['hi'][2],1950)
        desk=native_box([225,0,2270],[475,141,2370],*office.DESK)
        self.assertEqual(desk['lo'],[135.,0.,2200.])
        self.assertEqual(desk['hi'],[385.,141.,2300.])

    def test_data_panels_are_smaller_and_keep_all_six_views(self):
        self.assertEqual({r[0] for r in office.BOARDS},set(range(6)))
        area=sum(w*h for _,_,w,h,_ in office.BOARDS)
        original=380*190+300*150+210*145+300*150+300*150+350*175
        self.assertLess(area,original*.6)
        self.assertEqual(len(office.SCENES),6)
        for cell,center,w,h,normal in office.BOARDS:
            self.assertGreater(center[1]-h/2,1090)
            self.assertLess(center[1]+h/2,1320)

    def test_shell_has_neutral_walls_a_small_accent_and_bounded_native_materials(self):
        groups=office.shell();self.assertEqual(len(groups),10)
        for key,parts in groups.items():
            v,ids=join(parts)
            self.assertLess(len(v),65536);self.assertLess(int(ids.max()),len(v))
            self.assertTrue(np.isfinite(v['p']).all(),key)
        v,ids=join(groups['secondary']);p=v['p'][ids.reshape(-1,3)]
        area=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1).sum()/2
        self.assertLess(area,10_000)  # Less than one square metre of club inlay.
        v,ids=join(groups['crest']);self.assertEqual(len(ids),6)
        self.assertAlmostEqual(float(np.ptp(v['p'][:,0])),52.)

    def test_scene_overrides_apply_to_the_coach_office_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/room_pes_office.PREFIX/'office.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(scene_poses=office.SCENES)),encoding='utf8')
            self.assertEqual(room_pes_office.scene_pose(root,'Sala do treinador · quadro tático',[1]),office.SCENES['Sala do treinador · quadro tático'])
            self.assertEqual(room_pes_office.scene_pose(root,'Departamento médico · geral',[1,2,3]),[1,2,3])

    def test_repainting_clips_only_office_colour_and_preserves_medical_geometry(self):
        from rx3 import Rx3
        from room_interior_r72 import write_groups
        template=Path(__file__).resolve().parents[4]/'data/sceneassets/server16_dressing_room_v3/shared/locker_support_r68.rx3'
        # The medical wing is left of the shared wall; the office is right.
        v,ids=box((-600,1020,1800),(-400,1100,1900))
        office_v,office_i=box((0,1100,1800),(50,1150,1850))
        combined=join([(v,ids),(office_v,office_i)])
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'model.rx3'
            bindings=write_groups(template,{'secondary_wall_primary':[combined],'graphic':[(v,ids)]},target)
            rx=Rx3(target.read_bytes());before=read_mesh(rx,1)
            office.remove_coloured_office(rx,bindings)
            after,remaining=read_mesh(rx,0)
            self.assertEqual(len(remaining),len(ids))
            np.testing.assert_array_equal(after,v)
            np.testing.assert_array_equal(remaining,ids)
            untouched=read_mesh(rx,1)
            for a,b in zip(before,untouched):np.testing.assert_array_equal(a,b)

    def test_neutral_monitor_headers_keep_club_colours_in_a_thin_detail(self):
        context=dict(club=1043,club_name='Clube',date=20261111,colors=[[.8,0,0],[0,0,0]],neutral_office=True,coach={})
        def missing(_):raise FileNotFoundError()
        im=art.paint(context,missing)
        self.assertEqual(im.getpixel((1900,15))[:3],(24,32,39))
        self.assertEqual(im.getpixel((10,90))[:3],(204,0,0))
        self.assertEqual(im.getpixel((1900,130))[:3],(24,32,39))


if __name__=='__main__':unittest.main(verbosity=2)
