"""Door-only replacement, passage clearance and one finish for all three doors."""
import tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from rx3 import Rx3,VERTEX
from room_visual_r68 import read_mesh
import room_exit_door as exit_door
import room_annex_doors as doors
import room_v3,room_appearance as art,portable_paths,room_pes_office


class SingleDoorTests(unittest.TestCase):
    def test_two_single_leaves_preserve_openings_and_have_valid_native_attributes(self):
        g=doors.geometry();self.assertEqual(len(g['annex_leaves']),2)
        for (_,cx),(v,idx) in zip(doors.DOORS,g['annex_leaves']):
            self.assertEqual(len(idx),36)
            self.assertTrue(np.allclose(v['p'].min(0),[cx+63.8,doors.BOTTOM,doors.HINGE_Z],atol=.002))
            self.assertTrue(np.allclose(v['p'].max(0),[cx+68.2,doors.TOP,doors.HINGE_Z+doors.WIDTH],atol=.002))
            self.assertTrue(((v['uv']>=0)&(v['uv']<=1)).all())
        for parts in g.values():
            for v,idx in parts:
                self.assertTrue(np.isfinite(v['p']).all());self.assertLess(int(idx.max()),len(v))
                self.assertLess(np.abs((doors.unpack(v['n'])*doors.unpack(v['g'])).sum(1)).max(),.005)

    def test_existing_double_door_geometry_is_preserved_exactly(self):
        original=exit_door.geometry(False);combined=exit_door.geometry()
        for key,parts in original.items():
            for before,after in zip(parts,combined[key]):
                self.assertEqual(before[0].tobytes(),after[0].tobytes());self.assertEqual(before[1].tobytes(),after[1].tobytes())
        self.assertEqual(len(combined['leaves']),2);self.assertEqual(len(combined['annex_leaves']),2)

    def test_removal_preserves_every_other_triangle_and_fails_on_a_second_application(self):
        game=portable_paths.GAME
        for kind,name in [('interior','interior_r78.rx3'),('roles','room_roles_r77.rx3')]:
            rx=Rx3((game/room_v3.OLD/name).read_bytes())
            before=[read_mesh(rx,i) for i in range(len(rx.get(VERTEX)))]
            changes=doors.strip_old_fixtures(rx,kind);self.assertGreater(sum(changes.values()),30)
            for slot,(v,idx) in enumerate(before):
                triangles=idx.reshape(-1,3)
                if str(slot) in changes:triangles=triangles[~doors.fixture_mask(v,idx)]
                after,indices=read_mesh(rx,slot)
                self.assertEqual(sorted(v[t].tobytes() for t in triangles),sorted(after[t].tobytes() for t in indices.reshape(-1,3)),(kind,slot))
            with self.assertRaises(ValueError):doors.strip_old_fixtures(rx,kind)

    def test_one_choice_controls_both_leaf_materials_and_does_not_repaint_hardware(self):
        manifest=dict(model_files={'exit_door.rx3':'door.rx3'},exit_door_bindings=[dict(material=k,submesh=k) for k in exit_door.geometry()])
        context={'club':1043,'colors':[(.8,0,0),(0,0,0)]}
        with tempfile.TemporaryDirectory() as tmp:
            for choice in exit_door.FINISHES:
                captured={};images=[]
                def texture(game,image,name):images.append(image.copy());return str(len(images)-1)
                def add(key,model,tex,*args,**kwargs):captured[key]=images[int(tex)]
                with patch.object(room_v3,'texture',side_effect=texture):exit_door.prepare(manifest,context,tmp,add,[],dict(door_finish=choice))
                double=captured['v3_exit_door_leaves'];single=captured['v3_exit_door_annex_leaves']
                self.assertEqual(double.size,(512,1536));self.assertEqual(single.size,(768,1536))
                self.assertTrue(np.max(np.abs(np.asarray(double).mean((0,1))-np.asarray(single).mean((0,1))))<1)
                self.assertEqual(captured['v3_exit_door_metal'].getpixel((0,0)),(161,170,176,255))
                self.assertEqual(captured['v3_exit_door_frame'].getpixel((0,0)),(24,27,30,255))

    def test_custom_art_is_reused_by_all_leaves(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=art.club_folder(tmp,1043);folder.mkdir(parents=True)
            Image.new('RGBA',(256,512),(90,45,20,255)).save(folder/'exit-door.png')
            context={'club':1043,'colors':[(1,0,0),(0,0,0)]}
            for size in [(512,1536),(768,1536)]:
                image=exit_door.finish_image(tmp,context,'custom',size)
                self.assertEqual(image.getpixel((image.width//2,image.height//2)),(90,45,20,255))

    def test_collision_keeps_both_passages_free_and_follows_the_new_leaves(self):
        old=[dict(name='Salas / portas abertas / folha',lo=[243,2,1552],hi=[249,228,1660]),
             dict(name='Medical table',lo=[-980,0,1800],hi=[-810,80,1920])]
        result=doors.obstacles(old)
        self.assertEqual(old[0]['name'],'Salas / portas abertas / folha')
        self.assertIn(old[1],result);self.assertNotIn(old[0],result)
        for name,cx in doors.DOORS:
            for z in np.linspace(1500,1750,20):
                p=np.array([cx,175,z])
                self.assertFalse(any((p>=o['lo']).all() and (p<=o['hi']).all() for o in result))
            p=np.array([cx+66,175,1668])
            self.assertTrue(any((p>=o['lo']).all() and (p<=o['hi']).all() for o in result))

    def test_existing_camera_layout_and_room_collision_pipeline_remain_compatible(self):
        layout=json.loads((portable_paths.GAME/room_v3.OLD/'room_layout_r77.json').read_text(encoding='utf8'))
        adjusted=room_v3.camera_layout(layout)
        self.assertIsInstance(adjusted,dict)
        from room_fitted_shell import SIDE_SHIFT
        self.assertEqual(adjusted['room']['camera_bounds']['half_width'],layout['room']['camera_bounds']['half_width']+100-SIDE_SHIFT)
        for key in ('room','medical'):
            result=room_v3.obstacles(layout[key]['obstacles'])
            self.assertEqual(len([o for o in result if o['name'].startswith('Current Dressing Room / coach door')]),4)


if __name__=='__main__':unittest.main()
