"""Regressions for shipped room meshes, club themes, art and kit preservation."""
from pathlib import Path
import json, os, tempfile, unittest
import numpy as np
from PIL import Image
import portable_paths as portable
from rx3 import Rx3, VERTEX
from room_visual_r68 import read_mesh
from room_interior_r71 import (PREFIX, ART, sign_image, make_mural, art_stamp,
                               club_sign, ink_for_secondary)
from room_native_hanging_20261022 import source_shirt, hanger, surface


class InteriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage=Path(os.environ.get('ROOM_REVIEW_STAGE',str(portable.GAME/PREFIX)))

    def test_all_installed_mesh_buffers_are_valid(self):
        for name in ('room_roles_r71.rx3','scenery_r71.rx3','medical_room_r71.rx3','interior_r71.rx3'):
            rx=Rx3((self.stage/name).read_bytes())
            for slot in range(len(rx.get(VERTEX))):
                v,idx=read_mesh(rx,slot)
                self.assertGreater(len(v),0,name);self.assertEqual(len(idx)%3,0)
                self.assertLess(int(idx.max()),len(v));self.assertTrue(np.isfinite(v['p']).all())
                self.assertTrue(np.isfinite(v['uv']).all())

    def test_black_seat_seams_removed_without_removing_seat_geometry(self):
        old=Rx3((portable.GAME/PREFIX/'room_roles_r68.rx3').read_bytes())
        new=Rx3((self.stage/'room_roles_r71.rx3').read_bytes())
        def seams(rx):
            v,idx=read_mesh(rx,9);p=v['p'][idx.reshape(-1,3)]
            return int(((np.ptp(p[:,:,1],axis=1)<1.1)&np.all((p[:,:,1]>1058)&(p[:,:,1]<1060),axis=1)).sum())
        self.assertEqual(seams(old),35*12);self.assertEqual(seams(new),0)
        # Main seat/cushion role retains the low seating vertices.
        v,_=read_mesh(new,1);self.assertGreater(int(((v['p'][:,1]>1040)&(v['p'][:,1]<1100)).sum()),100)

    def test_ceiling_grid_and_leds_share_world_origin(self):
        spec=json.loads((self.stage/'interior_r71.json').read_text())
        for x,z in spec['lights']:self.assertEqual(x%60,30);self.assertEqual(z%60,30)
        for name in ('room_roles_r71.rx3','medical_room_r71.rx3'):
            v,_=read_mesh(Rx3((self.stage/name).read_bytes()),3)
            self.assertLess(float(np.max(np.abs(v['uv'].astype(float)-v['p'][:,[0,2]]/60))),.02)

    def test_hanger_arms_inside_both_native_shirt_types(self):
        for kind in (0,2):
            shirt,idx,_=source_shirt(kind);original=shirt.copy()
            v,_=hanger(shirt,idx);black=v['p'][v['uv'][:,0]<.5][::13]
            back=shirt['p'].copy();back[:,2]*=-1
            for x,y,z in black:
                hi=surface(shirt['p'],idx,float(x),float(y));lo=surface(back,idx,float(x),float(y))
                self.assertIsNotNone(hi);self.assertIsNotNone(lo)
                self.assertLess(float(z),hi);self.assertGreater(float(z),-lo)
            np.testing.assert_array_equal(shirt,original)

    def test_colors_and_contrast_for_white_and_dark_clubs(self):
        self.assertEqual(ink_for_secondary((255,255,255)),(18,20,23))
        self.assertEqual(ink_for_secondary((0,0,0)),(255,255,255))
        for colors in [((.84,0,.05),(0,0,0)),((.1,.4,.9),(1,1,1)),((.1,.65,.2),(.1,.2,.5))]:
            im=np.array(sign_image('Jogador de teste',colors));right=im[50:460,780:1950,:3]
            ink=ink_for_secondary(tuple(round(c*255) for c in colors[1]))
            self.assertGreater(int(np.all(right==ink,axis=2).sum()),300)

    def test_club_art_is_optional_replaceable_and_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ctx=dict(club=987654,club_name='Clube teste',colors=[[0,1,0],[1,1,1]])
            fallback=make_mural(ctx,None,root);self.assertEqual(fallback.size,(3072,1024))
            stamp=art_stamp(root,ctx['club']);folder=root/ART/str(ctx['club']);folder.mkdir(parents=True)
            Image.new('RGBA',(900,300),(70,30,150,255)).save(folder/'mural.png')
            self.assertNotEqual(art_stamp(root,ctx['club']),stamp)
            self.assertEqual(make_mural(ctx,None,root).getpixel((100,100)),(70,30,150,255))
            Image.new('RGBA',(800,200),(10,80,130,255)).save(folder/'sign_coach.png')
            self.assertEqual(club_sign(ctx,'COMISSÃO TÉCNICA','coach',game=root).getpixel((100,100)),(10,80,130,255))

    def test_walking_routes_and_open_door_positions_unchanged(self):
        spec=json.loads((self.stage/'interior_r71.json').read_text())
        self.assertFalse(spec['layout_changed'])
        # New collision boxes cover the actual new cabinet/fridge, not the
        # two established entrances or the clear aisle in front of them.
        for obstacle in spec['obstacles']:
            self.assertGreaterEqual(obstacle['lo'][0],300)
            self.assertGreaterEqual(obstacle['lo'][2],870)

    def test_fridge_front_is_open_behind_transparent_glass(self):
        rx=Rx3((self.stage/'interior_r71.rx3').read_bytes());v,idx=read_mesh(rx,0)
        p=v['p'][idx.reshape(-1,3)]
        front=np.all((p[:,:,0]>636)&(p[:,:,0]<704)&(p[:,:,1]>1092)&(p[:,:,1]<1231)&(p[:,:,2]<886),axis=1)
        self.assertFalse(front.any(),'Opaque cabinet face would hide every bottle')


if __name__=='__main__':unittest.main()
