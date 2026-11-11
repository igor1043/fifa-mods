"""Native drawer layout, club images and real compiled APT choice round-trips."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import room_v3 as room
import room_appearance as appearance
from rx3 import Rx3
from room_visual_r68 import read_mesh
from room_interior_r72 import write_groups
from test_room_personalization import open_personalization,commands


class DrawerTests(unittest.TestCase):
    def test_native_mesh_has_fitted_half_drawer_and_clear_left_cubby(self):
        groups=room.bay_groups()
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'locker.rx3'
            template=Path(__import__('portable_paths').GAME)/room.OLD/'locker_support_r68.rx3'
            bindings=write_groups(template,groups,target)
            native=Rx3(target.read_bytes())
            self.assertEqual([b['material'] for b in bindings],list(groups))
            drawer_slot=next(i for i,b in enumerate(bindings) if b['material']=='safe')
            drawer,indices=read_mesh(native,drawer_slot)
            np.testing.assert_allclose(drawer['p'].min(0),[1.4,237.7,81.3],atol=.001)
            np.testing.assert_allclose(drawer['p'].max(0),[40.6,258.3,84.2],atol=.001)
            self.assertLess(int(indices.max()),len(drawer))
            self.assertTrue(all(v['p'][:,1].max()<100 for v,_ in groups['linen']))
            # Empty left half: no old face board in front of its back panel.
            for vertices,_ in groups['wood']:
                lo,hi=vertices['p'].min(0),vertices['p'].max(0)
                self.assertFalse(lo[0]<-1 and hi[0]<41 and lo[1]>237 and hi[1]<260 and lo[2]>80)

    def test_badge_and_custom_image_surfaces_stay_on_the_drawer(self):
        groups=room.crest_groups()
        for key,width in [('bay',14),('bay_custom',38)]:
            v,_=groups[key][0];lo,hi=v['p'].min(0),v['p'].max(0)
            self.assertGreater(lo[0],1.4);self.assertLess(hi[0],40.6)
            self.assertGreater(lo[1],237.7);self.assertLess(hi[1],258.3)
            self.assertAlmostEqual(float(hi[0]-lo[0]),width,places=3)
            self.assertGreater(lo[2],84.2)
        self.assertEqual(list(groups)[:5],['bay','ceiling','floor','feature_wall','corner'])

    def test_none_custom_missing_and_crest_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertIsNone(room.drawer_front(root,1043,{'drawer_art':'none'}))
            self.assertIsNone(room.drawer_front(root,1043,{'drawer_art':'custom'}))
            self.assertEqual(room.drawer_front(root,1043,{'drawer_art':'crest'}),
                             ('data/ui/imgassets/crest/light/l1043.dds','','bay'))
            row=next(r for r in appearance.rows(root,1043) if r['key']=='drawer_art')
            self.assertEqual([o['value'] for o in row['options']],['crest','none','custom'])

    def test_custom_png_preserves_aspect_and_does_not_force_other_materials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=appearance.club_folder(root,1043);folder.mkdir(parents=True)
            Image.new('RGBA',(200,200),(255,50,10,255)).save(folder/'locker-box-front.png')
            preferences=root/appearance.PREFERENCES/'1043.json';preferences.parent.mkdir(parents=True)
            preferences.write_text('{"style":"default","drawer_art":"custom"}')
            self.assertEqual(appearance.preferences(root,1043)['style'],'default')
            captured=[]
            with patch.object(room,'texture',side_effect=lambda g,im,n:(captured.append(im.copy()) or 'custom.rx3')):
                self.assertEqual(room.drawer_front(root,1043,appearance.preferences(root,1043)),('custom.rx3','v3_cm','bay_custom'))
            im=captured[0];self.assertEqual(im.size,(1024,512))
            self.assertEqual(im.getbbox(),(256,0,768,512))
            self.assertEqual(im.getpixel((512,256)),(255,50,10,255))
            self.assertIsNone(appearance.asset(root,598,'locker_box_front'))

    def test_custom_dds_is_detected_and_existing_art_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=appearance.club_folder(root,1043);folder.mkdir(parents=True)
            image=folder/'locker-box-front.dds';Image.new('RGBA',(16,16),'blue').save(image)
            self.assertEqual(appearance.asset(root,1043,'locker_box_front'),image)
            self.assertEqual(appearance.preferences(root,1043)['drawer_art'],'custom')

    def test_full_draft_remains_exact_and_new_row_is_reachable(self):
        # Largest possible wire payload must survive the FIFA float32 VM.
        import math
        maximum=math.prod(len(items) for _,_,items in appearance.CATALOG[:appearance.PACKED_ROWS])-1
        self.assertLess(maximum,appearance.SEQUENCE_STRIDE)
        self.assertLess(maximum,2**24)
        vm,s,calls,_=open_personalization();vm.invoke(s.get('OpenRoomSettings'),s)
        index=next(i for i,row in enumerate(appearance.CATALOG) if row[0]=='drawer_art')
        vm.invoke(s.get('ShiftRoomSetting'),s,[index,2])
        self.assertEqual(s.get('settingsFocus'),index)
        self.assertEqual(s.get('settingIndex'+str(index)),2)
        vm.invoke(s.get('ApplyRoomSettings'),s)
        sequence=int(commands(calls)[-1].split('|')[3])
        self.assertEqual(appearance.decode_draft(__import__('portable_paths').GAME,1043,sequence,appearance.GROUPED_APPLY_CODE)['drawer_art'],'custom')

    def test_drawer_choice_persists_per_career_and_restores_after_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runtime=root/'ModCarrerMode/runtime';runtime.mkdir(parents=True)
            mailbox=runtime/'club_environment/room/runtime';mailbox.mkdir(parents=True)
            snap=runtime/'career_fce_snapshot.json'
            def career(name):snap.write_text(json.dumps(dict(pid=42,club=1043,savePath='C:\\Careers\\'+name+'\\DATA')))
            career('one');values=appearance.preferences(root,1043);values['drawer_art']='none'
            self.assertTrue(appearance.write_preferences(root,42,1043,'scope',1,120,values))
            career('two');self.assertEqual(appearance.preferences(root,1043)['drawer_art'],'crest')
            career('one');self.assertEqual(appearance.preferences(root,1043)['drawer_art'],'none')


if __name__=='__main__':unittest.main()
